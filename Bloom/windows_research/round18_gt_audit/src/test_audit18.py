"""Reproduce the defect and pitfalls; no estimator or selector is replaced."""
import unittest
import numpy as np
from audit18 import examine


class CountAuditTests(unittest.TestCase):
    def counts(self,values):return examine(np.repeat(np.arange(len(values),dtype=np.int64),values))

    def test_equal_repeat_collapse_two_to_five(self):
        for c in range(2,6):
            r=self.counts([c]*100)
            self.assertEqual(r['gap_c'],[c]);self.assertTrue(r['total_collapse'])
            self.assertEqual(r['original_total_mass'],0.)

    def test_singletons_are_separate_from_collapse(self):
        r=self.counts([1]*100)
        self.assertEqual(r['gap_c'],[1]);self.assertTrue(r['all_singletons'])
        self.assertFalse(r['total_collapse'])
        self.assertEqual(r['original_total_mass'],1.)
        self.assertAlmostEqual(r['literal_fallback_total_mass'],2.)
        self.assertTrue(r['preserve_singleton_fallback_rate_bit_equal'])

    def test_fallback_can_exceed_unit_mass(self):
        r=self.counts([1,1,2,2])
        self.assertAlmostEqual(r['original_total_mass'],2/3)
        self.assertAlmostEqual(r['literal_fallback_total_mass'],4/3)
        self.assertFalse(r['all_singletons'])

    def test_no_gap_is_not_probability_normalization(self):
        r=self.counts([1,2,3,4,5,6])
        self.assertEqual(r['gap_c'],[])
        self.assertTrue(r['literal_fallback_rate_bit_equal'])
        self.assertGreater(r['original_total_mass'],1.)

    def test_singleton_gap_with_some_repeated_keys(self):
        r=self.counts([1,1,6,6])
        self.assertEqual(r['gap_c'],[1]);self.assertTrue(r['singleton_gap_with_repeats'])
        self.assertFalse(r['all_singletons'])

    def test_no_gt_window_bin(self):
        r=self.counts([6]*100)
        self.assertEqual(r['gap_c'],[]);self.assertFalse(r['all_rates_zero'])
        self.assertTrue(r['literal_fallback_rate_bit_equal'])


if __name__=='__main__':unittest.main()
