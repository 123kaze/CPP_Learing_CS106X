import unittest
from unittest.mock import patch
from types import SimpleNamespace
import numpy as np
import zero17 as Z
from native_zero17 import ZeroTreeFilter


class ZeroTests(unittest.TestCase):
    def setUp(self):
        self.original=Z.E5.K;self.addCleanup(setattr,Z.E5,'K',self.original)
        rng=np.random.default_rng(1717)
        self.setup=SimpleNamespace(h1m=rng.integers(0,2**63,2000,dtype=np.uint64),h1q=rng.integers(0,2**63,10000,dtype=np.uint64))
        self.learn=rng.integers(0,1000,12000,dtype=np.int64)
        self.lm=Z.RA.ra4.summarize(self.learn,True)

    def test_zero_table_exact_physical_layout(self):
        for cache in Z.BF.CACHES.values():
            Z.E5.K=cache
            rows=Z.zero_table(self.setup,self.lm,4,36000)
            self.assertEqual(len(rows),13)
            for row in rows:
                c=Z.build_row(self.setup,None,4,row);st=c['structure']
                self.assertEqual(st.model_bytes,0);self.assertEqual(st.metadata_bytes,32)
                self.assertLessEqual(st.used_bytes,4096)
                self.assertEqual(row['bf_k'],int(st.data[2]))
                self.assertTrue(np.isfinite(row['pred']) and row['pred']>=0)

    def test_zero_only_never_calls_model_or_learned_table(self):
        with patch.object(Z.RA,'candidate_table',side_effect=AssertionError('model path called')):
            c,info=Z.select(self.setup,None,self.lm,4,36000,trees=())
        self.assertEqual(c['trees'],0);self.assertEqual(info['built'],5)
        self.assertEqual(info['learned_candidates'],0)

    def test_empty_or_invalid_search_rejected(self):
        with self.assertRaises(ValueError):Z.select(self.setup,None,self.lm,4,36000,trees=(),include_zero=False)
        with self.assertRaises(ValueError):Z.select(self.setup,None,self.lm,4,36000,topk=0)

    def test_norepeat_zero_prediction_is_static_fpr(self):
        lm=Z.RA.ra4.summarize(np.arange(1000),True)
        rows=Z.zero_table(self.setup,lm,4,3000)
        for row in rows:self.assertAlmostEqual(row['pred'],float(row['seg_fpr_pred'][0]*3000),places=9)
        self.assertEqual(min(rows,key=lambda r:(r['pred'],r['frac']))['frac'],0)

    def test_reload_has_no_model_or_features(self):
        for mode,cache in Z.BF.CACHES.items():
            c=Z.BF.build(self.setup,4,.2,cache)
            restored=np.frombuffer(c['structure'].data.tobytes(),np.uint64).copy()
            f=ZeroTreeFilter(restored,c['cache_bytes'],mode,self.setup.h1m)
            self.assertTrue(np.array_equal(f.probe_hashes(self.setup.h1q)==1,c['structure'].fp_static))
            self.assertTrue((f.probe_hashes(self.setup.h1m)==1).all())
            self.assertEqual(f.deployment_bytes,c['structure'].used_bytes)
            self.assertFalse(hasattr(f,'model'));self.assertFalse(hasattr(f,'features'))
            if mode=='fp64':self.assertEqual(f.external_index_bytes,0)

    def test_explicit_feedback_only(self):
        for mode,cache in Z.BF.CACHES.items():
            c=Z.BF.build(self.setup,4,.2,cache);f=ZeroTreeFilter(c['structure'].data,c['cache_bytes'],mode,self.setup.h1m)
            key=self.setup.h1q[np.flatnonzero(c['structure'].fp_static)[0]]
            before=f.state.copy();self.assertEqual(int(f.probe_hashes([key])[0]),1)
            self.assertTrue(np.array_equal(before,f.state))
            self.assertIn(f.feedback_absent(key),(1,2));self.assertEqual(int(f.probe_hashes([key])[0]),2)
            self.assertTrue((f.probe_hashes(self.setup.h1m)==1).all())

    def test_index_format_requires_member_index(self):
        c=Z.BF.build(self.setup,4,.2,Z.BF.CACHES['index'])
        with self.assertRaises(ValueError):ZeroTreeFilter(c['structure'].data,c['cache_bytes'],'index')


if __name__=='__main__':unittest.main()
