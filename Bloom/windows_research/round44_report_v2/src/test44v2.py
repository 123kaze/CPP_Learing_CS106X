import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from report44v2 import merged_diagnostic,paired

class Tests(unittest.TestCase):
    def test_shared_member_field_once(self):
        m=dict(members=123,distinct_negative_keys=456,GET_queries=999,GET_time_reversals=2);q=dict(eligible_for_method_comparison=True);d=dict(members=123,seed=4401)
        out=merged_diagnostic('toy',m,q,d);self.assertEqual(out['members'],123);self.assertEqual(out['seed'],4401)
    def test_mismatched_member_field_rejected(self):
        m=dict(members=123,distinct_negative_keys=456,GET_queries=999,GET_time_reversals=2);q=dict(eligible_for_method_comparison=True)
        with self.assertRaises(ValueError):merged_diagnostic('toy',m,q,dict(members=124))
    def test_pairs_keep_tie_and_loss(self):
        out=paired([(0,1),(2,2),(5,1)]);self.assertEqual((out['wins'],out['ties'],out['losses']),(1,1,1));self.assertEqual(out['median_smoothed_ratio'],1.)

if __name__=='__main__':unittest.main()
