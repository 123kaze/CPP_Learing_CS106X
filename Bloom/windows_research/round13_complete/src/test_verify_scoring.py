"""Regression tests on a temporary, data-free copy of the archived records."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from verify_scoring import ROOT, verify


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='ra13-scoring-verify-')
        cls.wr = Path(cls.temp.name) / 'windows_research'
        record = json.loads((ROOT / 'results/scoring_verification.json').read_text())
        inputs = json.loads((ROOT / 'results/scoring/manifest.json').read_text())['inputs']
        for rel in record['sources']:
            if rel in inputs:
                continue
            dest = cls.wr / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT.parent / rel, dest)
        cls.root = cls.wr / ROOT.name

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def altered(self, rel, mutate):
        path = self.root / rel
        original = path.read_bytes()
        self.addCleanup(path.write_bytes, original)
        obj = json.loads(original)
        mutate(obj)
        path.write_text(json.dumps(obj))

    def rejected(self):
        with self.assertRaises((AssertionError, FileNotFoundError, KeyError)):
            verify(self.root)

    def test_complete_data_free_archive(self):
        r = verify(self.root)
        self.assertEqual(r['verified_pairs'], 30)
        self.assertEqual(r['workload_records'], 120)
        self.assertFalse(r['checked_raw_inputs'])

    def test_missing_build(self):
        path = self.root / 'results/scoring/paper_url_64_leaf_rep0.json'
        data = path.read_bytes()
        self.addCleanup(path.write_bytes, data)
        path.unlink()
        self.rejected()

    def test_extra_build(self):
        path = self.root / 'results/scoring/paper_url_64_leaf_rep9.json'
        path.write_text('{}')
        self.addCleanup(path.unlink)
        self.rejected()

    def test_pair_score_mismatch(self):
        self.altered('results/scoring/paper_url_64_leaf_rep0.json',
                     lambda r: r['score_sha256'].update({'1': '0' * 64}))
        self.rejected()

    def test_missing_prefix_in_both_modes(self):
        for mode in ('loop', 'leaf'):
            self.altered(f'results/scoring/paper_url_64_{mode}_rep0.json',
                         lambda r: r['score_sha256'].pop('200'))
        self.rejected()

    def test_nonfinite_time(self):
        self.altered('results/scoring/paper_url_64_leaf_rep0.json',
                     lambda r: r.update(train_s=float('nan')))
        self.rejected()

    def test_wrong_summary(self):
        self.altered('results/scoring_summary.json',
                     lambda rows: rows[0].update(median_paired_speedup=99))
        self.rejected()

    def test_wrong_round8_reference(self):
        self.altered('../round8_paper_data/results/paper_url_64_RA6_rep0.json',
                     lambda r: r['workloads']['once'].update(fp=999999))
        self.rejected()

    def test_changed_frozen_source(self):
        path = self.root / 'src/leaf_scores.py'
        original = path.read_bytes()
        self.addCleanup(path.write_bytes, original)
        path.write_bytes(original + b'\n# unexpected change\n')
        self.rejected()

    def test_raw_inputs_required_only_when_requested(self):
        with self.assertRaises(FileNotFoundError):
            verify(self.root, with_inputs=True)


if __name__ == '__main__':
    unittest.main()
