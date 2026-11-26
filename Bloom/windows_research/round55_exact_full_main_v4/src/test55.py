import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import *
from unittest.mock import patch
sys.path.insert(0,str(WR/'round53_index_free_recheck_v3/src'))
import test53

class Tests(unittest.TestCase):
    def test_paper_stacked_fallback(self):
        self.assertTrue(Path(STACK.__file__).as_posix().endswith('round6_bucket/src/stacked_full.py'))
        flags=np.ones(3,np.bool_);g=dict(structure=SimpleNamespace(fp_static=flags,used_bytes=1024));bases={.1:(100,g)}
        s=SimpleNamespace(h1q=np.array([1,2,3],np.uint64),h1m=np.array([4],np.uint64));learn=np.array([0,0,1,2],np.int64)
        calls=[]
        def layer(setup,base,known,side,b2):
            calls.append(len(known))
            return dict(fp=np.zeros(3,np.bool_)) if len(known)==1 else None
        with patch.object(STACK.X7,'stacked_layers',side_effect=layer):
            fp,frac,b2,used=STACK.stacked_fp(s,bases,g,1,learn)
        self.assertTrue(np.array_equal(fp,flags));self.assertEqual((frac,b2,used),(0.,0.,1024));self.assertIn(3,calls)
    def test_slot_cost(self):
        for w in (8,9,33,128):
            cache=K.Cache(w);old=RA.ra4.slot_bits
            with slot_cost(cache):
                for slots in (0,1,4,100,1024):
                    nb=max(1,int(np.ceil(slots/4)));physical=K.ARRAY_HEADER+K.HEAD+nb*(4*(w+4)+1)
                    self.assertEqual(RA.ra4.slot_bits(slots),physical*8/(4*nb))
            self.assertIs(RA.ra4.slot_bits,old)
    def test_workspace_restore(self):
        old=E5.build;cache=E5.K
        with self.assertRaises(ValueError):
            with scope(K.Cache(8)):raise ValueError()
        self.assertIs(E5.build,old);self.assertIs(E5.K,cache)
    def test_warm_cache_not_cold_subtraction(self):
        blob=np.frombuffer(b'ab',np.uint8).copy();off=np.array([0,1,2],np.int64);hashes=np.zeros(2,np.uint64);flags=np.ones(2,np.bool_);idx=np.array([0,1],np.int64)
        cache=K.Cache(8);spec=cache.layout(1024);state=cache.allocate(spec)
        args=(hashes,blob,off,idx,flags,state,spec['buckets'],8,2**62)
        self.assertEqual(K.replay(np.array([0,0],np.int64),*args)[0],1)
        self.assertEqual(K.replay(np.array([0,1,0],np.int64),*args)[0],1)
        state=cache.allocate(spec);args=(hashes,blob,off,idx,flags,state,spec['buckets'],8,2**62)
        self.assertEqual(K.replay(np.array([0,1,0],np.int64),*args)[0],2)

if __name__=='__main__':
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test53),unittest.defaultTestLoader.loadTestsFromTestCase(Tests)])
    assert suite.countTestCases()==16
    result=unittest.TextTestRunner(verbosity=2).run(suite);raise SystemExit(0 if result.wasSuccessful() else 1)
