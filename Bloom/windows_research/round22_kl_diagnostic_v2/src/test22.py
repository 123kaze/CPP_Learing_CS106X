"""Small tests only. No frozen imports, true cache files, candidates or replay."""
import ast
import json
import math
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import numpy as np
from scipy.optimize import minimize
from control22 import ROOT, protocol, serial_gate
from math22 import A, capped, theory_layers, fit_eb, dm_relative, integer_fpr


class MathTests(unittest.TestCase):
    def test_clipped_gate_reversal(self):
        t=theory_layers([.5,.5],[.99,.01],[.5,.5],.1/A,.3/A)
        self.assertTrue(t['raw_KL_says_win']);self.assertFalse(t['capped_same_W_says_win'])
        self.assertFalse(t['interior_legal'])
        self.assertAlmostEqual(t['same_W_capped_ratio'],1.107617796970651)

    def test_B_interior_and_both_clipping_directions(self):
        t=theory_layers([.5,.5],[.99,.01],[.5,.5],3/A)
        self.assertTrue(t['B']['interior_equality_applicable'])
        b=theory_layers([.5,.5],[.99,.01],[.5,.5],.1/A)['B']
        self.assertLess(b['capped_loss_ratio'],b['arithmetic_geometric_factor'])
        b=theory_layers([.5,.1,.4],[.15,.45,.4],[.2,.15,.65],.6/A)['B']
        self.assertGreater(b['capped_loss_ratio'],b['arithmetic_geometric_factor'])

    def test_zero_mass_and_empty(self):
        e=capped([1,1,0],[1,0,10],1)
        self.assertEqual(e[1],1);self.assertEqual(e[2],0);self.assertGreater(e[0],0)
        t=theory_layers([1,1],[1,0],[.5,.5],1)
        self.assertTrue(t['KL_infinite']);self.assertIsNone(t['relaxed_FP'])
        t=theory_layers([1,1],[0,0],[.5,.5],1)
        self.assertEqual(t['capped_FP'],0);self.assertIsNone(t['r'])

    def test_independent_small_convex_solver(self):
        rng=np.random.default_rng(221119)
        for _ in range(12):
            p,r=[rng.dirichlet(np.ones(4)*2) for _ in range(2)]
            beta=float(rng.uniform(.02,2))
            e=capped(p,r,beta/A)
            fit=minimize(lambda x:float(r@np.exp(-x)),np.ones(4)*beta,
                         jac=lambda x:-r*np.exp(-x),bounds=[(0,None)]*4,
                         constraints=[dict(type='eq',fun=lambda x:float(p@x)-beta,jac=lambda x:p)],
                         method='SLSQP',options={'ftol':1e-12})
            self.assertTrue(fit.success);self.assertAlmostEqual(float(r@e),fit.fun,places=10)

    def test_EB_endpoints_and_singletons_counterexample(self):
        settings=protocol()['EB']
        u,meta=fit_eb([8,2],[.5,.5],settings)
        self.assertAlmostEqual(meta['alpha'],3.29683,places=3)
        self.assertFalse(np.allclose(u,[.5,.5]))
        self.assertEqual(fit_eb([5,5],[.5,.5],settings)[1]['endpoint'],'infinity-or-numerical-tie')
        self.assertEqual(fit_eb([10,0],[.5,.5],settings)[1]['endpoint'],'zero-limit')
        for s in ([0,0],[1,0]):
            self.assertEqual(fit_eb(s,[.5,.5],settings)[1]['endpoint'],'unidentified-use-h')

    def test_DM_stable_high_alpha(self):
        s=np.array([8,2]);h=np.array([.5,.5]);alpha=1e9
        exact=sum(float(np.log1p(np.arange(1,int(n))/(alpha*x)).sum()) for n,x in zip(s,h))
        exact-=float(np.log1p(np.arange(1,int(s.sum()))/alpha).sum())
        self.assertAlmostEqual(dm_relative(alpha,s,h),exact,places=20)

    def test_raw_KL_not_plugin_guarantee(self):
        t=theory_layers([.5,.5],[.99,.01],[.01,.99],3/A,3/A)
        self.assertTrue(t['raw_KL_says_win'])
        mismatch=t['B']['capped_loss_ratio']
        self.assertGreater(t['same_W_capped_ratio']*mismatch,9)

    def test_integer_and_cost_units(self):
        eps=integer_fpr([10,0,10],[100,0,0],[7,0,0])
        self.assertEqual(eps[1],0);self.assertEqual(eps[2],1)
        self.assertGreater(eps[0],0);self.assertLess(eps[0],1)
        t=theory_layers([100,100],[1,1],[.5,.5],800,1600)
        self.assertAlmostEqual(t['extra_cost_delta'],4*A)


class ControlTests(unittest.TestCase):
    def setUp(self):
        scratch=ROOT/'test_artifacts';scratch.mkdir(exist_ok=True)
        self.tmp=tempfile.TemporaryDirectory(dir=scratch)
        self.p=Path(self.tmp.name)
    def tearDown(self):self.tmp.cleanup()
    def test_gate_absent_running_failure_rejected(self):
        path=self.p/'completion.json'
        with self.assertRaises(RuntimeError):serial_gate(path)
        for status in ('running','failed','error'):
            path.write_text(json.dumps(dict(status=status)))
            with self.assertRaises(RuntimeError):serial_gate(path)
    def test_complete_gate(self):
        path=self.p/'completion.json';path.write_text('{"status":"complete"}')
        self.assertEqual(serial_gate(path)['mode'],'completed')
    def test_gate_reads_completion_once(self):
        path=self.p/'completion.json';path.write_text('{"status":"complete"}')
        original=Path.read_bytes
        calls=[]
        def counted(obj):
            calls.append(obj)
            return original(obj)
        with patch.object(Path,'read_bytes',counted):
            serial_gate(path)
        self.assertEqual(calls,[path])
    def test_explicit_release(self):
        p=self.p/'release.json'
        p.write_text(json.dumps(dict(prior_round='round21_shared_replay_v2',prior_status='stopped',
            approved_for_round22=True,recorded_by='coordinator',reason='synthetic test, not real release',
            prior_jobs_confirmed_stopped=True)))
        self.assertEqual(serial_gate(self.p/'missing',p)['mode'],'explicit-failed-or-stopped-release')
        p.write_text('{"approved_for_round22":true}')
        with self.assertRaises(ValueError):serial_gate(self.p/'missing',p)
    def test_fixed_small_matrix(self):
        p=protocol()
        self.assertEqual(len(p['matrix']),13)
        self.assertEqual(p['matrix'][0],dict(dataset='url',budget_kib=128,workload='zipf1.0-全部'))
        self.assertEqual(len(p['zero_cache_fractions']),13)
        self.assertNotIn('mawi2024_flow',[r['dataset'] for r in p['matrix']])
        self.assertEqual(len(p['static_tree_prefixes']),4)
    def test_worker_is_deferred_and_syntax_valid(self):
        for path in (ROOT/'src').glob('*.py'):
            ast.parse(path.read_text(),filename=str(path))
        source=(ROOT/'src/worker22.py').read_text()
        self.assertLess(source.index('ticket = check_ticket'),source.index('import numpy as np'))
        self.assertLess(source.index('heuristic = min(hchoices)'),source.index('tail_freq = np.bincount(tail'))
        self.assertNotIn('import zero17', (ROOT/'src/control22.py').read_text())
    def test_numpy_scalar_result_serialization(self):
        from control22 import save
        t=theory_layers([100,100],[1,1],[.5,.5],800,1600)
        path=self.p/'scalars.json'
        save(path,dict(theory=t,flag=np.bool_(True),count=np.int64(5),value=np.float32(.5)))
        result=json.loads(path.read_text())
        self.assertIs(type(result['flag']),bool)
        self.assertIs(type(result['count']),int)
        self.assertEqual(result['count'],5)
        self.assertEqual(result['theory']['raw_KL_says_win'],bool(t['raw_KL_says_win']))
    def test_numpy_nonfinite_rejected(self):
        from control22 import save
        for value in (np.float32(np.nan),np.float64(np.inf)):
            with self.assertRaises(ValueError):save(self.p/'invalid.json',dict(value=value))
        self.assertFalse((self.p/'invalid.json').exists())
    def test_arrays_not_silently_serialized(self):
        from control22 import save
        with self.assertRaises(TypeError):save(self.p/'array.json',dict(value=np.array([1,2])))

    def test_no_nonfinite_JSON(self):
        t=theory_layers([1,1],[1,0],[.5,.5],1)
        json.dumps(t,allow_nan=False)


if __name__=='__main__':unittest.main(verbosity=2)
