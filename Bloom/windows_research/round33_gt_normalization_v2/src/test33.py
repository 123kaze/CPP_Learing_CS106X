import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from normalize33 import *
import unittest


class Tests(unittest.TestCase):
    def test_three_query_example_and_count_semantics(self):
        lm=summarize19(np.array([0,1,1],np.int64));before=lm.rate.copy()
        a,da=normalize(lm,'SeenNormalize');b,db=normalize(lm,'TotalNormalize')
        np.testing.assert_allclose(a.rate,[2/9,4/9]);np.testing.assert_allclose(b.rate,[.25,.5]);self.assertAlmostEqual(a.unseen_mass,1/3);self.assertEqual(b.unseen_mass,.25)
        self.assertEqual((a.L,a.N1,b.L,b.N1),(3,1,3,1));self.assertIs(a.counts,lm.counts);np.testing.assert_array_equal(lm.rate,before)
        self.assertAlmostEqual(da['raw_total_mass'],4/3);self.assertAlmostEqual(db['total_mass'],1)

    def test_singletons_are_bitwise_noop(self):
        lm=summarize19(np.arange(100,dtype=np.int64))
        for arm in ARMS:
            q,d=normalize(lm,arm);np.testing.assert_array_equal(q.rate.view(np.uint8),lm.rate.view(np.uint8));self.assertFalse(d['changed']);self.assertEqual(q.unseen_mass,1.)

    def test_probability_constraints(self):
        rng=np.random.default_rng(33)
        for _ in range(30):
            lm=summarize19(rng.integers(0,20,100,dtype=np.int64))
            for arm in ARMS[1:]:
                q,d=normalize(lm,arm);self.assertAlmostEqual(q.rate.sum()+q.unseen_mass,1.,places=12);self.assertTrue(np.all((q.rate>=0)&(q.rate<=1)));self.assertEqual(q.N1,lm.N1);self.assertEqual(q.L,lm.L)
        with self.assertRaises(ValueError):normalize(SimpleNamespace(L=0),'GT19')

    def test_both_prediction_stages_use_new_unseen_mass(self):
        lm=summarize19(np.array([0,1,1],np.int64));h=np.full(1000,.001)
        td=SimpleNamespace(seg_q=np.array([0,1],np.int64),g=np.ones(1000),h=h)
        setup=SimpleNamespace(h1q=np.array([11,22],np.uint64));c=dict(cache_bytes=0,structure=SimpleNamespace(fp_static=np.array([True,True])))
        for arm in ARMS:
            q,d=normalize(lm,arm)
            pop=ORIGINAL_POPULATION(q,td,30,RA.Config(new_mix=0.)) if arm=='GT19' else normalized_population(q,td,30,RA.Config(new_mix=0.))
            pred=ORIGINAL_BUCKET(setup,q,td,c,30,np.ones(1000)) if arm=='GT19' else normalized_bucket(setup,q,td,c,30,np.ones(1000))
            target=40 if arm=='GT19' else 30
            self.assertAlmostEqual(pop.Mg[0].sum(),target,places=10);self.assertAlmostEqual(pred,target,places=10)

    def test_control_and_exception_restore_original_functions(self):
        for arm in ARMS:
            try:
                with adapted(arm):
                    self.assertIs(RA.population,ORIGINAL_POPULATION if arm=='GT19' else normalized_population)
                    self.assertIs(ra6.bucket_prediction,ORIGINAL_BUCKET if arm=='GT19' else normalized_bucket)
                    raise RuntimeError('injected failure')
            except RuntimeError:pass
            self.assertIs(RA.population,ORIGINAL_POPULATION);self.assertIs(ra6.bucket_prediction,ORIGINAL_BUCKET);self.assertIs(RA.candidate_table,ORIGINAL_TABLE)


if __name__=='__main__':unittest.main()
