import unittest
import numpy as np
from scipy.optimize import check_grad,minimize
from loss25 import *


class LossTests(unittest.TestCase):
    def test_inner_clipped_solver_against_independent_convex_optimization(self):
        rng=np.random.default_rng(2501)
        for _ in range(12):
            p,q=rng.dirichlet(np.ones(5),size=2);beta=float(rng.uniform(.02,2.))
            J,e,lam,x=capped(p,q,beta)
            fit=minimize(lambda v:float(q@np.exp(-v)),np.full(5,beta),jac=lambda v:-q*np.exp(-v),
                bounds=[(0,None)]*5,constraints=[dict(type='eq',fun=lambda v:float(p@v)-beta,jac=lambda v:p)],
                method='SLSQP',options=dict(ftol=1e-12,maxiter=200))
            self.assertTrue(fit.success);self.assertAlmostEqual(J,fit.fun,places=8)
            self.assertTrue((e<=1).all())

    def test_soft_assignment_is_probability_and_gradient_sums_zero(self):
        a,d=soft_regions(np.array([-100.,-1.,0.,2.,100.]),np.array([-2.,-.5,.5,2.]),.5)
        self.assertTrue((a>=0).all());self.assertTrue(np.allclose(a.sum(axis=1),1))
        self.assertTrue(np.allclose(d.sum(axis=1),0))

    def test_envelope_gradient_with_respect_to_scores(self):
        rng=np.random.default_rng(25);scores=rng.normal(size=50);y=np.arange(50)%2==0;cuts=np.array([-2.,-.4,.5,2.])
        for beta in (.05,.5,2.):
            err=check_grad(lambda s:surrogate_scores(s,y,cuts,.7,beta)[0],lambda s:surrogate_scores(s,y,cuts,.7,beta)[1],scores)
            self.assertLess(err,1e-5)

    def test_network_gradient(self):
        rng=np.random.default_rng(25);Z=rng.normal(size=(50,3));y=np.arange(50)%2==0
        w=rng.normal(0,.2,3*8+16+1);args=(Z,y,np.array([-1.,-.3,.4,1.]),.6,.5)
        err=check_grad(lambda v:objective(v,*args)[0],lambda v:objective(v,*args)[1],w)
        self.assertLess(err,1e-5)

    def test_saturation_and_constant_scores_stay_finite(self):
        y=np.arange(20)%2==0
        for s in (np.zeros(20),np.full(20,1000.)):
            value,gradient,meta=surrogate_scores(s,y,np.array([-2.,-1.,1.,2.]),.5,.1)
            self.assertTrue(np.isfinite(value));self.assertTrue(np.isfinite(gradient).all())
            self.assertAlmostEqual(meta['J'],np.exp(-.1))


if __name__=='__main__':unittest.main(verbosity=2)
