import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import data44 as D
import unittest,tempfile
np=D.np

class Tests(unittest.TestCase):
    def test_csv_schema_and_client_ignored(self):
        row=b'1580000000,"ns:a,b",6,0,private-client,get,0\n'
        t,k,n,op=D.decode(row);self.assertEqual(k,b'ns:a,b');self.assertEqual((n,op),(6,'get'))
        self.assertEqual(len((t,k,n,op)),4)
    def test_schema_rejects_bad_records(self):
        for row in (b'1,a,1,0,get,0\n',b'nan,a,1,0,c,get,0\n',b'1,,0,0,c,get,0\n',b'x'*65537):
            with self.assertRaises(ValueError):D.decode(row)
    def test_features_are_key_only(self):
        f=D.lexical(b'abc:12_X-999');self.assertEqual(len(f),24)
        self.assertEqual(f[0],12);self.assertEqual(f[1],1);self.assertEqual(f[10],5)
        self.assertEqual(f[16],3);self.assertEqual(f[19],3);self.assertEqual(f[21],1)
    def test_prefix_not_whole_trace_catalogue(self):
        keys=[b'a',b'b',b'c',b'd'];first=[0,1,4,10];seq=[0,1,0,1,2,0,2,1,2,0,3,1,3,2,3,0]
        d=D.assemble(keys,first,seq)
        np.testing.assert_array_equal(d['y'],[True,True,False,False]);self.assertEqual(int(d['catalog_end']),4);self.assertEqual(int(d['learn_end']),8)
        # A later read of a previously unseen key does not retroactively enter the checkpoint.
        self.assertFalse(d['y'][3]);self.assertEqual(d['trace'][10],3)
    def test_split_uses_learning_only_negatives(self):
        keys=[f'key:{i}'.encode() for i in range(800)]
        seq=list(range(200))+list(range(200,400))+list(range(400,800))
        d=D.assemble(keys,list(range(800)),seq)
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.npz';np.savez(p,**d)
            s,X,l,t=D.prepare(p,4401)
            self.assertEqual(int(s.y.sum()),200)
            self.assertTrue((d['first'][s.split['neg_train']|s.split['neg_val']]<400).all())
            self.assertTrue((d['first'][s.split['neg_train']|s.split['neg_val']]>=200).all())
            self.assertTrue(s.split['neg_test'][400:].all())
            self.assertEqual(len(t),400);self.assertGreater(len(l),0)
    def test_budgets_and_small_duplicate_collapse(self):
        self.assertEqual(D.budgets(1000),(4,));self.assertEqual(D.budgets(65536),(16,32,64))
    def test_exact_original_key_storage(self):
        keys=[b'a'*128,b'a'*128+b'b',b'ns:member'];d=D.assemble(keys,[0,4,1],[0,2,0,2,1,1,0,2])
        recovered=[d['blob'][d['offsets'][i]:d['offsets'][i+1]].tobytes() for i in range(3)]
        self.assertEqual(recovered,keys);self.assertEqual(len(np.unique(d['ids'])),3)

if __name__=='__main__':unittest.main()
