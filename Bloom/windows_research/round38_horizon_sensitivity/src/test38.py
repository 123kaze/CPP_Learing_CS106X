import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import horizon38 as H
from types import SimpleNamespace
from unittest.mock import patch
import inspect,unittest
np=H.np


class Tests(unittest.TestCase):
    def test_matrix_and_horizon_direction(self):
        self.assertEqual(len(H.cases()),21)
        self.assertEqual(len({(r['dataset'],r['seed'],r['budget_kib']) for r in H.cases()}),21)
        self.assertEqual(H.horizons(7,25),dict(quarter=6,matched=25,fourfold=100,three_learning=21))
        self.assertEqual(H.horizons(1,3)['quarter'],1)
        self.assertEqual({H.rule_order(i)[0] for i in range(4)},set(H.RULES))
        for l,a in ((0,1),(1,0),(-1,3),(1,2.5)):
            with self.assertRaises(ValueError):H.horizons(l,a)

    def test_both_stages_receive_same_H_and_objects_unchanged(self):
        rows=[dict(trees=1,frac=.1,cache_bytes=100,slots=4,pred=1.,weights=np.ones(3),seg_fpr_pred=np.ones(3))]
        def table(*args,**kwargs):return rows
        def bucket(*args,**kwargs):return 2.
        def select(s,sc,lm,kib,h):
            got=H.RA.candidate_table(s,sc,lm,kib,h,object());self.assertIs(got,rows)
            H.R6.bucket_prediction(s,lm,object(),object(),h,np.ones(3))
            return {'chosen':True},dict(built=1,trees=1,frac=.1)
        with patch.object(H,'ORIGINAL_TABLE',table),patch.object(H.RA,'candidate_table',table),patch.object(H,'ORIGINAL_BUCKET',bucket),patch.object(H.R6,'bucket_prediction',bucket),patch.object(H.R6,'select6',select):
            _,info=H.select(object(),{},object(),8,123)
            self.assertEqual(info['stage1_H'],[123]);self.assertEqual(info['stage2_H'],[123])
            self.assertIs(H.RA.candidate_table,table);self.assertIs(H.R6.bucket_prediction,bucket)
        self.assertNotIn('tail',inspect.signature(H.select).parameters)
        self.assertNotIn('stream',inspect.signature(H.select).parameters)

    def test_exception_restores_observers(self):
        table=H.RA.candidate_table;bucket=H.R6.bucket_prediction
        with self.assertRaisesRegex(RuntimeError,'fixture'):
            with H.observe(7):raise RuntimeError('fixture')
        self.assertIs(H.RA.candidate_table,table);self.assertIs(H.R6.bucket_prediction,bucket)
        with H.observe(7):
            with self.assertRaises(AssertionError):
                with H.observe(7):pass
        self.assertIs(H.RA.candidate_table,table)

    def test_payload_comparison_is_bytewise_not_just_numeric(self):
        a={'x':np.array([0.,1.])};b={'x':np.array([-0.,1.])}
        self.assertFalse(H.arrays_equal(a,b))
        self.assertTrue(H.arrays_equal(a,{'x':a['x'].copy()}))
        self.assertFalse(H.arrays_equal(a,{'x':a['x'].astype(np.float32)}))

    def test_fp64_needs_no_index_and_collision_is_not_zero_FN_claim(self):
        class Setup:
            h1m=np.array([2],np.uint64)
            h1q=np.array([2,3],np.uint64)
            @property
            def member_hashes(self):raise AssertionError('fp64 read forbidden member index')
        s=Setup();cache=H.CACHES['fp64'];spec=cache.layout(512)
        c=dict(cache_bytes=spec['allocated_bytes'],structure=SimpleNamespace(fp_static=np.ones(2,np.bool_)))
        result,_=H.evaluate(c,np.array([0,0,1,1],np.int64),s,None,'fp64')
        self.assertEqual(result['fp'],2);self.assertEqual(result['hits'],2)
        self.assertEqual(result['member_cache_hits_final'],1)
        self.assertGreater(result['fp64_ideal_hash_bound_per_query'],0.)
        cache=H.CACHES['index'];spec=cache.layout(512);c['cache_bytes']=spec['allocated_bytes']
        safe=H.E5.E.CC.safe_prefix_lengths(np.sort(s.h1m),s.h1q)
        result,_=H.evaluate(c,np.array([0,0,1,1],np.int64),s,safe,'index')
        self.assertEqual(result['member_cache_hits_final'],0)
        self.assertGreaterEqual(result['bypasses'],2)


if __name__=='__main__':unittest.main()
