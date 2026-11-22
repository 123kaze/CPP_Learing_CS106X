import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from data36 import decode_line, parse, np
from diagnose36 import split, auc, qualify, SEEDS, splitmix64, diagnose
import gzip
import json
import tempfile
import unittest


def row(target, status, day='31/Aug/1995', size=b'1'):
    return b'private-client.invalid - - ['+day.encode()+b':23:59:59 -0400] "GET '+target+b' HTTP/1.0" '+str(status).encode()+b' '+size+b'\n'


class Tests(unittest.TestCase):
    def test_both_documented_formats_and_no_identity(self):
        parsed, why = decode_line(row(b'/a?q=1', 404))
        self.assertIsNone(why); self.assertEqual(parsed[1:3], (b'/a?q=1',404))
        self.assertNotIn('private-client', repr(parsed))
        other, why = decode_line(b'private-client.invalid [Thu Jun 01 00:00:00 1995] "GET /a" 200 0\n')
        self.assertIsNone(why); self.assertEqual(other[0].isoformat(),'1995-06-01T00:00:00-04:00')
        self.assertEqual(other[2],200)
        self.assertEqual(decode_line(row(b'/a',200).replace(b'GET ',b'POST '))[1],'non_GET')
        self.assertEqual(decode_line(row(b'/a extra token',404))[1],'malformed_GET_request')
        self.assertEqual(decode_line(row(b'/a',404,day='31/Feb/1995'))[1],'invalid_GET_timestamp')

    def test_cross_month_order_conflicts_and_zero_bytes(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder); a=root/'a.gz'; b=root/'b.gz'; out=root/'prepared.npz'
            with gzip.open(a,'wb') as f:
                for target,status in ((b'/m',200),(b'/late',404),(b'/expire',200),(b'/n',404),(b'/m',304),(b'/n',404)):
                    f.write(row(target,status))
                f.write(b'malformed\n'); f.write(row(b'/post',200).replace(b'GET ',b'POST '))
            with gzip.open(b,'wb') as f:
                for target,status in ((b'/late',200),(b'/expire',404),(b'/n',404),(b'/zero',200),(b'/n',404),(b'/other',500)):
                    f.write(row(target,status,day='01/Sep/1995',size=b'0'))
            meta=parse([a,b],out,'fixture')
            self.assertEqual((meta['lines'],meta['parsed_GET'],meta['members'],meta['negative_keys']),(14,12,2,1))
            self.assertEqual(meta['recorded_order_time_reversals'],0)
            self.assertEqual(meta['conflicting_keys'],2)
            self.assertEqual(meta['retained_404_requests'],4)
            self.assertEqual(meta['retained_success_requests'],3)
            self.assertAlmostEqual(meta['retained_404_fraction'],2/3)
            self.assertEqual(meta['development_404_then_future_success_keys'],1)
            self.assertEqual(meta['development_success_then_future_404_keys'],1)
            self.assertEqual(meta['boundary_GET_ordinal'],3)
            self.assertEqual(set(meta['monthly_status_counts']),{'1995-08','1995-09'})
            self.assertNotIn('private-client', json.dumps(meta))
            with np.load(out,allow_pickle=False) as d:
                self.assertEqual(len(d['trace']),7)
                self.assertTrue(np.all(np.diff(d['order'])>=0))
                self.assertEqual(d['X'].shape,(3,20))
            with self.assertRaises(AssertionError):parse([a,b],out,'fixture')

    def test_split_is_key_disjoint_and_future_negatives_not_training(self):
        ids=np.arange(2500,dtype=np.uint64); y=np.arange(2500)%3==0
        first=np.where(np.arange(2500)<1000,0,100)
        for seed in SEEDS:
            s=split(ids,y,first,50,seed)
            self.assertTrue(np.all(first[s['neg_train']|s['neg_val']]<50))
            self.assertFalse(np.any(s['neg_test']&(s['neg_train']|s['neg_val'])))
            self.assertTrue(np.all(s['neg_test'][(~y)&(first>=50)]))
            self.assertTrue(np.array_equal(s['neg_test']|s['neg_val']|s['neg_train'],~y))
        self.assertEqual(int(splitmix64(np.array([0],np.uint64))[0]),0xe220a8397b1dcdaf)

    def test_auc_ties_and_direction(self):
        y=np.array([False,True,False,True])
        self.assertEqual(auc(y,np.array([0.,1.,0.,1.])),1.)
        self.assertEqual(auc(y,np.ones(4)),.5)
        self.assertEqual(auc(y,np.array([1.,0.,1.,0.])),0.)

    def test_fixed_model_and_region_accounting_on_synthetic_data(self):
        rng=np.random.default_rng(36);n=4000
        X=rng.integers(0,8,size=(n,20)).astype(np.float32);y=X[:,0]<3
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'synthetic.npz'
            np.savez(p,ids=np.arange(n,dtype=np.uint64),X=X,y=y,first=np.arange(n),
                     trace=np.tile(np.arange(n),3),order=np.arange(3*n),boundary=np.int64(3000))
            r=diagnose(p,SEEDS[0])
            self.assertEqual(r['status'],'complete');self.assertEqual(r['actual_trees'],16)
            self.assertEqual(sum(g['learning_requests'] for g in r['regions']),r['learning_requests'])
            self.assertEqual(sum(g['members'] for g in r['regions']),int(y.sum()))
            self.assertGreater(r['development_auc'],.9)
            self.assertGreater(r['tail_new_key_request_fraction'],0.)

    def test_predeclared_qualification_uses_no_filter_results(self):
        meta=dict(members=10000,negative_keys=1000,retained_404_requests=10000,retained_404_fraction=.9)
        base=dict(learning_requests=1000,tail_requests=1000,train_negatives=20,validation_negatives=20,
                  feature_overlap_fraction=.01,development_auc=.7,learning_repeat_fraction=.1,supported_regions=2,region_repeat_gap=.1)
        rows=[dict(base,seed=s) for s in SEEDS]
        expected=qualify(meta,rows)
        self.assertTrue(expected['eligible_for_full_comparison'])
        for r in rows:r['irrelevant_RA_fp']=100000000
        self.assertEqual(qualify(meta,rows),expected)
        meta['members']=9999
        self.assertEqual(qualify(meta,rows)['failed_checks'],['members_ge_10000'])
        rows[0]['development_auc']=None
        self.assertFalse(qualify(meta,rows)['eligible_for_full_comparison'])


if __name__=='__main__':unittest.main()
