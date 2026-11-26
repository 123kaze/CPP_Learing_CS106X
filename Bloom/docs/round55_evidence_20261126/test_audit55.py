"""Mutation tests for the evidence auditor, using one archived case as fixture."""
import copy
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('audit55', HERE / 'audit55.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
ROOT = HERE.parents[1] / 'windows_research/round55_exact_full_main_v4'


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.item = A.read(ROOT / 'results/caida_1024/case_000.json')
        self.case = copy.deepcopy(self.item['case'])

    def test_valid_archived_case(self):
        self.assertEqual(len(A.audit_case(self.item, self.case)), 14)

    def test_reject_changed_reference(self):
        self.item['case']['historical_Gama_fp'] += 1
        with self.assertRaisesRegex(ValueError, 'case identity'):
            A.audit_case(self.item, self.case)

    def test_reject_uncharged_cache_header(self):
        row = self.item['rows'][1]
        row['cache_bytes'] -= 112
        row['total_bytes'] -= 112
        with self.assertRaisesRegex(ValueError, 'exact-key physical bytes'):
            A.audit_case(self.item, self.case)

    def test_reject_index(self):
        self.item['rows'][0]['member_index_bytes'] = 8
        with self.assertRaisesRegex(ValueError, 'FN/index'):
            A.audit_case(self.item, self.case)

    def test_reject_fn(self):
        self.item['rows'][0]['member_fn'] = 1
        with self.assertRaisesRegex(ValueError, 'FN/index'):
            A.audit_case(self.item, self.case)

    def test_reject_wrong_shortlist_choice(self):
        row = next(r for r in self.item['rows'] if r['method'] == 'RA6-top3')
        row['selection_info']['pred'] += 1
        with self.assertRaisesRegex(ValueError, 'chosen prediction'):
            A.audit_case(self.item, self.case)

    def test_reject_missing_warm_replay(self):
        row = next(r for r in self.item['rows'] if r['method'] == 'RA6-warm')
        row['learning_warm_s'] = 0
        with self.assertRaisesRegex(ValueError, 'actual learning replay'):
            A.audit_case(self.item, self.case)

    def test_reject_invented_oracle(self):
        self.item['hindsight_h_fp'] += 1
        with self.assertRaisesRegex(ValueError, 'hindsight minimum'):
            A.audit_case(self.item, self.case)

    def test_reject_weighted_candidate_drift(self):
        top = self.item['top10'][0]
        row = next(r for r in self.item['weighted_full'] if (r['trees'], r['frac']) == (top['trees'], top['frac']))
        row['fp'] += 1
        with self.assertRaisesRegex(ValueError, 'full-grid and top10 consistency'):
            A.audit_case(self.item, self.case)


if __name__ == '__main__':
    unittest.main(verbosity=2)
