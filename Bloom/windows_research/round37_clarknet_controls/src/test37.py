import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from control37 import E5,RA,M,W,np,budgets,region_masses,controls
from types import SimpleNamespace
from unittest.mock import patch
import unittest


class Tests(unittest.TestCase):
    def test_budget_rule_is_member_based(self):
        self.assertEqual(budgets(32581),(8,16,32))
        self.assertEqual(budgets(10000),(4,5,10))

    def test_traffic_and_miss_use_same_baseline_epsilon(self):
        calls=[]
        class Population:
            def misses(self,e,S,sa):
                calls.append((e.copy(),S,sa))
                return np.array([2.,3.,4.,5.]) if S==0 else np.array([1.,2.,1.,2.])
        td=SimpleNamespace(h=np.array([.1,.2,.3,.4]));reg=np.array([0,0,1,1]);eps=np.array([.2,.3])
        out=region_masses(Population(),td,reg,eps,40)
        np.testing.assert_allclose(out['h'],[.3,.7])
        np.testing.assert_allclose(out['traffic'],[5,9]+RA.FLOOR*14*np.array([.3,.7]))
        np.testing.assert_allclose(out['miss'],[3,3]+RA.FLOOR*6*np.array([.3,.7]))
        self.assertEqual([x[1] for x in calls],[0,40])
        for e,_,sa in calls:np.testing.assert_array_equal(e,eps[reg]);self.assertTrue(sa)

    def test_conditional_continuous_identity(self):
        result=M.identity(np.array([100.,200.,300.]),np.array([.6,.3,.1]),np.array([10.,70.,20.]),10000)
        self.assertTrue(result['interior'])
        self.assertAlmostEqual(result['conditional_baseline_fp']/result['conditional_reweighted_fp'],result['arithmetic_geometric_factor'],places=9)

    def test_fixed_physical_configuration_and_member_safety(self):
        key=('synthetic_control37',1)
        setup=SimpleNamespace(name=key[0],h1m=E5.C.splitmix64(np.arange(500,dtype=np.uint64)),
                              h1q=E5.C.splitmix64(np.arange(1000,1100,dtype=np.uint64)))
        safe=E5.E.CC.safe_prefix_lengths(np.sort(setup.h1m),setup.h1q)
        boundaries=np.arange(0,1001,200,dtype=np.int64)
        td=SimpleNamespace(seg_m=np.arange(500,dtype=np.int64)*2,seg_q=np.arange(100,dtype=np.int64)*10,
                           h=np.full(1000,.001),fixed=1024,model_bytes=400,metadata_bytes=181,overhead_bytes=443)
        cache,S=E5.cache_alloc(4096,.1)
        anchor=dict(trees=1,frac=.1,cache_bytes=cache,slots=S,
                    structure=SimpleNamespace(est_fpr=.1,b=boundaries,f=np.full(5,.1)))
        class Population:
            def misses(self,e,slots,setassoc):
                return np.ones(1000) if slots==0 else np.linspace(.1,1.,1000)
        with patch.object(E5,'candidates',return_value=[anchor]),patch.object(E5,'tree',return_value=td),patch.object(RA,'population',return_value=Population()),patch.dict(E5.R._MODEL_ARRAYS,{key:{'toy':np.zeros(4)}}):
            result=controls(setup,{},object(),300,4,np.tile(np.arange(100,dtype=np.int64),3),safe)
        self.assertEqual(result['status'],'complete')
        self.assertEqual([r['arm'] for r in result['rows']],['h','traffic','miss'])
        self.assertFalse(result['actual_clock_fixed_T_condition'])
        for r in result['rows']:
            self.assertEqual(r['processed'],300);self.assertEqual(r['member_fn'],0)
            self.assertEqual(r['cache_physical_bytes'],cache);self.assertLessEqual(r['total_bytes'],4096)
            self.assertLessEqual(r['physical']['used_bits'],result['bf_budget_bits'])
        np.testing.assert_array_equal(result['partition'],boundaries)


if __name__=='__main__':unittest.main()
