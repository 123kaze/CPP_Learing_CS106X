import unittest
import numpy as np
from summarize19 import summarize19
from entry19 import ORIGINAL_SUMMARIZE,patched,ra4


class SummaryRepairTests(unittest.TestCase):
    def stream(self,counts):return np.repeat(np.arange(len(counts),dtype=np.int64),counts)

    def check_invariant(self,counts,gt=True):
        x=self.stream(counts);a=ORIGINAL_SUMMARIZE(x,gt);b=summarize19(x,gt)
        self.assertEqual(a.keys.tobytes(),b.keys.tobytes());self.assertEqual(a.counts.tobytes(),b.counts.tobytes())
        for field in ('L','N1','state_bytes'):self.assertEqual(getattr(a,field),getattr(b,field))
        nc=np.bincount(a.counts)
        gaps=[c for c in range(2,6) if c<len(nc) and nc[c]>0 and (c+1>=len(nc) or nc[c+1]==0)] if gt else []
        mask=np.isin(a.counts,gaps)
        self.assertTrue(np.all(b.rate>=a.rate))
        self.assertEqual(a.rate[~mask].tobytes(),b.rate[~mask].tobytes())
        self.assertTrue(np.array_equal(b.rate[mask],a.counts[mask]/a.L))
        self.assertTrue(np.isfinite(b.rate).all())
        return a,b

    def test_equal_twice(self):
        a,b=self.check_invariant([2]*100);self.assertTrue((a.rate==0).all());self.assertTrue((b.rate>0).all())

    def test_equal_three(self):self.check_invariant([3]*100)
    def test_equal_four(self):self.check_invariant([4]*100)
    def test_equal_five(self):self.check_invariant([5]*100)

    def test_all_singletons_bit_exact(self):
        a,b=self.check_invariant([1]*100);self.assertEqual(a.rate.tobytes(),b.rate.tobytes());self.assertEqual(b.N1,b.L)

    def test_singletons_next_to_repeats(self):
        _,b=self.check_invariant([1,1,3,3]);self.assertTrue(np.array_equal(b.rate,np.array([0,0,3,3])/8))

    def test_two_separate_missing_classes(self):
        _,b=self.check_invariant([2,2,4,4]);self.assertTrue(np.array_equal(b.rate,np.array([2,2,4,4])/12))

    def test_mixed_frequency(self):self.check_invariant([1,1,2,2,4,6,10])

    def test_nonempty_next_bin_untouched(self):
        a,b=self.check_invariant([1,2,3,4,5,6]);self.assertEqual(a.rate.tobytes(),b.rate.tobytes())

    def test_no_gt_bit_exact(self):
        a,b=self.check_invariant([1,1,2,2,4,4],False);self.assertEqual(a.rate.tobytes(),b.rate.tobytes())

    def test_random_histogram_invariant(self):
        rng=np.random.default_rng(1919)
        for _ in range(100):self.check_invariant(rng.integers(1,16,int(rng.integers(1,100))))

    def test_runtime_hook_and_exception_restore(self):
        try:
            with patched():
                self.assertIs(ra4.summarize,summarize19)
                self.assertTrue((ra4.summarize(self.stream([2]*10)).rate>0).all())
                raise RuntimeError('intentional')
        except RuntimeError:pass
        self.assertIs(ra4.summarize,ORIGINAL_SUMMARIZE)

    def test_bucket_prediction_recovers_nonzero_seen_mass(self):
        import sys
        from entry19 import WR
        from types import SimpleNamespace
        sys.path.insert(0,str(WR/'round6_bucket/src'))
        import ra6
        x=self.stream([2]*100)
        a=ORIGINAL_SUMMARIZE(x,True);b=summarize19(x,True)
        c=dict(cache_bytes=0,structure=SimpleNamespace(fp_static=np.ones(100,np.bool_)))
        td=SimpleNamespace(h=np.ones(1))
        self.assertEqual(ra6.bucket_prediction(None,a,td,c,1000,np.array([.5])),0.)
        self.assertAlmostEqual(ra6.bucket_prediction(None,b,td,c,1000,np.array([.5])),1000.)

    def test_no_probability_normalization_claim(self):
        _,b=self.check_invariant([1,1,2,2]);self.assertAlmostEqual(float(b.rate.sum()+b.N1/b.L),4/3)


if __name__=='__main__':unittest.main()
