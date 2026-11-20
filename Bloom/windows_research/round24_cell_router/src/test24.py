import unittest
import numpy as np
from cells24 import *


class RouterTests(unittest.TestCase):
    def test_budget_and_roundtrip(self):
        rng=np.random.default_rng(24);X=rng.normal(size=(1000,3)).astype(np.float32)
        X[:100,0]=0.;y=(X[:,0]*X[:,1]>.1)
        a=np.arange(len(X));split=dict(member_train=y&(a%2==0),neg_train=(~y)&(a%3==0),neg_val=(~y)&(a%3==1))
        h=C.splitmix64(a.astype(np.uint64))
        for bins in (16,32):
            arrays,flags,meta=fit_build(X,y,split,h,[0,1],bins,8)
            actual=query(X,h,a,**arrays)
            self.assertTrue(np.array_equal(actual,flags));self.assertTrue(actual[y].all())
            self.assertLessEqual(meta['total_bytes'],8192)
            self.assertEqual(meta['packed_table_payload_bytes'],(3*bins*bins+63)//64*8)
            copies={k:np.frombuffer(v.tobytes(),v.dtype).copy() for k,v in arrays.items()}
            self.assertTrue(np.array_equal(actual,query(X,h,a,**copies)))

    def test_unknown_cell_and_boundary_stay_in_range(self):
        X=np.tile(np.arange(100,dtype=np.float32)[:,None],(1,2));y=np.arange(100)%2==0
        split=dict(member_train=y,neg_train=~y,neg_val=~y)
        h=C.splitmix64(np.arange(100,dtype=np.uint64));a,_,_=fit_build(X,y,split,h,[0,1],16,4)
        for row in (np.array([-1000.,1000.]),np.array([1.,1.]),np.array([50.,-1000.])):
            self.assertIn(lookup_region(row,a['header'],a['edges'],a['route']),range(5))


if __name__=='__main__':unittest.main(verbosity=2)
