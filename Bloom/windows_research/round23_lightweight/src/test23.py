"""Synthetic checks only; no real data or throughput conclusion."""
import unittest
import numpy as np
from scipy.optimize import check_grad
import models23 as M
import filter23 as F


class ModelFilterTests(unittest.TestCase):
    def setUp(self):
        rng=np.random.default_rng(23)
        self.X=rng.normal(size=(400,4)).astype(np.float32)
        self.X[:,-1]=1.
        self.y=(self.X[:,0]+.6*self.X[:,1]>.1)
        self.train=np.arange(400)%3!=0

    def test_model_native_matches_reference(self):
        for name in M.MODELS:
            meta,a,reference=M.fit(name,self.X[self.train],self.y[self.train],1)
            raw=M.native_scores(self.X,*M.arguments(meta,a))
            self.assertTrue(np.allclose(raw,reference(self.X),rtol=1e-9,atol=1e-9),name)
            self.assertTrue(np.isfinite(raw).all(),name)
            copies={k:np.frombuffer(v.tobytes(),v.dtype).copy() for k,v in a.items()}
            self.assertTrue(np.array_equal(raw,M.native_scores(self.X,*M.arguments(meta,copies))),name)

    def test_training_gradients(self):
        rng=np.random.default_rng(24);Z=self.X[:30].astype(float);y=self.y[:30].astype(float)
        objectives=[(M.linear_objective,rng.normal(0,.1,5),Z),
                    (M.additive_objective,rng.normal(0,.1,4*16+1),rng.integers(0,16,(30,4))),
                    (M.mlp_objective,rng.normal(0,.1,4*8+2*8+1),Z)]
        for fn,w,x in objectives:
            err=check_grad(lambda z:fn(z,x,y)[0],lambda z:fn(z,x,y)[1],w)
            self.assertLess(err,1e-5,fn.__name__)

    def test_all_members_and_budget(self):
        h=F.C.splitmix64(np.arange(len(self.X),dtype=np.uint64))
        split={'neg_val':(~self.y)&(np.arange(len(self.X))%2==0)}
        for name in M.MODELS:
            meta,a,_=M.fit(name,self.X[self.train],self.y[self.train],1)
            raw=M.native_scores(self.X,*M.arguments(meta,a))
            layout,flags,bytes_=F.build(meta,a,raw,self.y,split,h,32)
            actual=F.query(self.X,h,np.arange(len(h)),meta,a,layout)
            self.assertTrue(actual[self.y].all(),name)
            self.assertTrue(np.array_equal(actual,flags),name)
            self.assertLessEqual(bytes_['total_bytes'],32768)
            copies={k:v.copy() for k,v in layout.items()}
            self.assertTrue(np.array_equal(actual,F.query(self.X,h,np.arange(len(h)),meta,a,copies)))

    def test_additive_edges_and_out_of_range(self):
        meta,a,reference=M.fit('Additive16',self.X[self.train],self.y[self.train],1)
        rows=np.vstack([np.full(4,-1e6),np.full(4,1e6),a['edges'].reshape(4,15)[:,4]])
        self.assertTrue(np.allclose(M.native_scores(rows,*M.arguments(meta,a)),reference(rows)))

    def test_pure_bf_matches_frozen(self):
        h=F.C.splitmix64(np.arange(400,dtype=np.uint64))
        data=F.B.allocate(int(self.y.sum()),4096,0);F.B.insert_all(data,h[self.y])
        expected=F.B.query_all(data,h)
        self.assertTrue(np.array_equal(expected,F.bf_query(data,h,np.arange(len(h)))))
        self.assertTrue(expected[self.y].all())


if __name__=='__main__':unittest.main(verbosity=2)
