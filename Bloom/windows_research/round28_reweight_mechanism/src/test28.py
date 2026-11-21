import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mechanism28 import *
from scipy.optimize import minimize
import unittest
import itertools


class Tests(unittest.TestCase):
    def test_identity_independent_convex_solver(self):
        rng=np.random.default_rng(28)
        for bits in (10.,100.,1000.):
            for _ in range(8):
                n=rng.integers(1,50,5).astype(float);h=rng.dirichlet(np.ones(5));M=rng.dirichlet(np.ones(5))
                result=identity(n,h,M,bits);e=np.array(result['reweighted_epsilon'])
                opt=minimize(lambda z:float(M@np.exp(-z)),np.full(5,A*bits/n.sum()),jac=lambda z:-M*np.exp(-z),method='SLSQP',bounds=[(0,None)]*5,
                             constraints=[{'type':'ineq','fun':lambda z:A*bits-n@z,'jac':lambda z:-n}],options={'ftol':1e-12,'maxiter':1000})
                self.assertTrue(opt.success);self.assertAlmostEqual(float(M@e),opt.fun,places=7)

    def test_equal_residual_is_no_gain(self):
        n=np.array([1,2,3,4,5]);h=np.ones(5)/5
        for bits in (2,200):
            q=identity(n,h,7*h,bits)
            self.assertAlmostEqual(q['predicted_gain'],0.,places=12);self.assertAlmostEqual(q['conditional_gain'],0.,places=12)

    def test_ttl_exact_finite_enumeration(self):
        prob=np.array([.2,.3,.5]);H=6
        for T in (0,1,2,6,7):
            total=np.zeros(3)
            for sequence in itertools.product(range(3),repeat=H):
                stream=np.array(sequence,np.int64);total+=np.prod(prob[stream])*ttl_misses(stream,3,T)
            _,m,_,_=masses(prob,np.arange(3),T,H,3)
            np.testing.assert_allclose(total,m,rtol=1e-12,atol=1e-12)
        for T in (0,1,10):
            _,m,_,_=masses(np.array([1.]),np.array([0]),T,6,1)
            self.assertEqual(m[0],6 if T==0 else 1)

    def test_regional_mass_unchanged(self):
        reg=np.repeat(np.arange(5),100);h=np.arange(1,6,dtype=float);h/=h.sum()
        for amp in (-1.5,0,1.5):
            prob,actual,_=probabilities(reg,h,amp);np.testing.assert_allclose(np.bincount(reg,weights=prob),h)

    def test_physical_bf_and_clock(self):
        mh=E5.C.splitmix64(np.arange(1000,dtype=np.uint64));qh=E5.C.splitmix64(np.arange(1000,2000,dtype=np.uint64))
        rm=np.arange(1000,dtype=np.int32)%5;rq=rm.copy();n=np.bincount(rm);h=np.ones(5)/5
        safe=E5.E.CC.safe_prefix_lengths(np.sort(mh),qh)
        for bits in (2000,8000):
            flags,m=physical(n,capped(n,h,bits),mh,qh,rm,rq,bits)
            self.assertLessEqual(m['payload_bytes']*8,bits);self.assertEqual(m['member_fn'],0)
            stream=np.tile(np.arange(1000,dtype=np.int64),3);r,cb=clock(stream,qh,safe,flags,mh)
            self.assertEqual(r['processed'],3000);self.assertLessEqual(cb,2048);self.assertLessEqual(r['fp'],int(flags[stream].sum()))


if __name__=='__main__':unittest.main()
