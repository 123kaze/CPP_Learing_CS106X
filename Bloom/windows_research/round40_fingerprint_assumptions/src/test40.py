from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit40 import occupancy,lower_bound,enumerate_small,native_contract
from fractions import Fraction
from itertools import product
from collections import Counter
import unittest


class Tests(unittest.TestCase):
    def test_occupancy_matches_full_small_enumeration(self):
        for m,n in ((2,2),(3,3),(4,2)):
            count=Counter(len(set(x)) for x in product(range(m),repeat=n))
            self.assertEqual(occupancy(m,n),{k:Fraction(v,m**n) for k,v in count.items()})

    def test_fn_lower_bound_matches_sufficient_event(self):
        result=enumerate_small()
        self.assertEqual(result['assignments'],256)
        self.assertEqual(result['actual'],Fraction(25,64))
        self.assertEqual(result['sufficient'],lower_bound(2,4,2,1,2))
        self.assertGreater(result['sufficient'],result['naive'])
        self.assertGreaterEqual(result['actual'],result['sufficient'])

    def test_no_eviction_capacity_recovers_any_collision_probability(self):
        self.assertEqual(lower_bound(3,4,2,2,2),1-Fraction(7,8)**2)
        self.assertGreater(lower_bound(64,64,64,4,5),Fraction(4,2**64))

    def test_frozen_native_parameters_and_alias_semantics(self):
        r=native_contract()
        self.assertEqual((r['BF_bits'],r['BF_probes'],r['fp64_slots']),(64,1,4))
        self.assertTrue(r['fp64_representation_alias_hits'])
        self.assertEqual(r['index_alias_safe_length'],65)
        self.assertEqual(r['index_member_hits'],0)


if __name__=='__main__':unittest.main()
