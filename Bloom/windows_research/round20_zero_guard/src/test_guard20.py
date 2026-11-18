import unittest
from types import SimpleNamespace
import numpy as np
import guard20 as G


class GateTests(unittest.TestCase):
    def test_tie_prefers_zero(self):self.assertEqual(G.gate_family(100,100),'zero')
    def test_zero_wins(self):self.assertEqual(G.gate_family(80,100),'zero')
    def test_learned_wins(self):self.assertEqual(G.gate_family(100,80),'learned')
    def test_negative_rejected(self):
        with self.assertRaises(ValueError):G.gate_family(-1,0)
    def test_empirical_bound_all_pairs(self):
        for a in range(25):
            for b in range(25):
                chosen=a if G.gate_family(a,b)=='zero' else b
                self.assertEqual(chosen,min(a,b))
    def test_no_claim_on_future(self):
        chosen=G.gate_family(2,3)
        tail={'zero':10,'learned':1}
        self.assertGreater(tail[chosen],min(tail.values()))
    def test_bf_replay_matches_frozen_with_cutoffs(self):
        original=G.E5.K;self.addCleanup(setattr,G.E5,'K',original)
        rng=np.random.default_rng(2020)
        setup=SimpleNamespace(h1m=rng.integers(0,2**63,1000,dtype=np.uint64),h1q=rng.integers(0,2**63,3000,dtype=np.uint64))
        learn=rng.integers(0,3000,30000,dtype=np.int64)
        safe=G.E5.E.CC.safe_prefix_lengths(np.sort(setup.h1m),setup.h1q)
        for cache in G.BF.CACHES.values():
            G.E5.K=cache
            candidates=[G.BF.build(setup,2,f,cache) for f in G.E5.FRACS]
            ours,fp,records,_=G.replay_bf_family(candidates,learn,setup,safe)
            old,fps=G.E5.replay_best(candidates,learn,setup,safe)
            self.assertEqual(ours['frac'],old['frac'])
            self.assertEqual(fp,fps[0,old['frac']][0])
            self.assertEqual(len(records),13)
            allfp=[G.E5.evaluate(c,learn,setup,safe)['fp'] for c in candidates]
            self.assertEqual(fp,min(allfp))
            self.assertLessEqual(sum(r['processed'] for r in records),12*len(learn))
    def test_zero_deployment_bit_exact(self):
        rng=np.random.default_rng(20)
        setup=SimpleNamespace(h1m=rng.integers(0,2**63,1000,dtype=np.uint64),h1q=rng.integers(0,2**63,3000,dtype=np.uint64))
        c=G.BF.build(setup,2,.2,G.BF.CACHES['index'])
        f=G.ZeroTreeFilter(c['structure'].data,c['cache_bytes'],'index',setup.h1m)
        self.assertTrue(np.array_equal(f.probe_hashes(setup.h1q)==1,c['structure'].fp_static))
        self.assertEqual(f.deployment_bytes,c['structure'].used_bytes)


if __name__=='__main__':unittest.main()
