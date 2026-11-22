"""Small checks of frozen zero-member/zero-weight code, not a convergence proof."""
import sys
from pathlib import Path
BLOOM=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(BLOOM/'windows_research/round41_exact_key_budget/src'))
from exact41 import RA,E5,np
import unittest

class Tests(unittest.TestCase):
    def test_zero_member_and_zero_weight(self):
        n=np.array([0.,4.,3.]);M=np.array([5.,0.,2.]);bits=64.
        e=RA.ra4.eps_closed(M,n,bits)
        self.assertEqual(e[0],0.);self.assertEqual(e[1],1.)
        self.assertTrue(0<e[2]<=1)
        used=(n[1:]*-np.log(e[1:])).sum()/np.log(2)**2
        self.assertLessEqual(used,bits+1e-10)
        self.assertAlmostEqual(used,bits,places=9)
    def test_zero_budget_or_all_zero_weight(self):
        n=np.array([0.,2.,3.])
        np.testing.assert_array_equal(RA.ra4.eps_closed(np.ones(3),n,0),[0.,1.,1.])
        np.testing.assert_array_equal(RA.ra4.eps_closed(np.zeros(3),n,64),[0.,1.,1.])
    def test_empty_vs_pass_in_deployed_region(self):
        from types import SimpleNamespace
        td=SimpleNamespace(g=np.zeros(1000,np.int64));td.g[300]=7
        bounds=np.array([0,200,400,600,800,1000],np.int64)
        _,n,_,m,kind=E5.region_bits(td,bounds,np.ones(5))
        np.testing.assert_array_equal(n,[0,7,0,0,0]);self.assertTrue((m==0).all())
        np.testing.assert_array_equal(kind,[E5.C.EMPTY,E5.C.PASS,E5.C.EMPTY,E5.C.EMPTY,E5.C.EMPTY])
    def test_amgm_scale_not_variance(self):
        p=np.array([.2,.3,.5]);r=np.array([.1,1.,3.])
        def gain(x):return float((p*x).sum()/np.exp((p*np.log(x)).sum()))
        self.assertGreaterEqual(gain(r),1.)
        self.assertAlmostEqual(gain(10*r),gain(r),places=12)
        self.assertAlmostEqual(np.var(10*r),100*np.var(r),places=10)

if __name__=='__main__':unittest.main()
