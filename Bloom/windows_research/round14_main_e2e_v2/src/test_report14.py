"""Data-free archival checks, including intentional corruptions in temporary copies."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from report14 import ROOT, collect, render, optional_upstream


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='ra14-report-')
        cls.bloom = Path(cls.tmp.name)
        cls.root = cls.bloom / 'windows_research' / ROOT.name
        record = json.loads((ROOT / 'results/verification.json').read_text())
        for rel in record['sources']:
            if optional_upstream(rel) or '/cache/' in rel or '/inputs/' in rel or rel.startswith('original_baselines/gama/data/'):
                continue
            dest = cls.bloom / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT.parents[1] / rel, dest)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def change(self, rel, mutate):
        p = self.root / rel
        original = p.read_bytes()
        self.addCleanup(p.write_bytes, original)
        r = json.loads(original)
        mutate(r)
        p.write_text(json.dumps(r))

    def reject(self):
        with self.assertRaises((AssertionError, FileNotFoundError, KeyError)):
            collect(self.root)

    def test_plain_clone_and_reproducible_tables(self):
        rows, tables, verification = collect(self.root)
        self.assertEqual(len(rows), 72)
        self.assertEqual(len(tables), 8)
        self.assertTrue(verification['unavailable_upstream_sources'])
        self.assertFalse(verification['checked_raw_inputs'])
        for name, text in render(rows, tables).items():
            self.assertEqual(text.encode(), (ROOT / 'results' / name).read_bytes())

    def test_missing_run(self):
        p = self.root / 'results/main/url_128_rep0_leaf.json'
        original = p.read_bytes()
        self.addCleanup(p.write_bytes, original)
        p.unlink()
        self.reject()

    def test_extra_run(self):
        p = self.root / 'results/main/url_128_rep9_leaf.json'
        p.write_text('{}')
        self.addCleanup(p.unlink)
        self.reject()

    def test_score_mismatch(self):
        self.change('results/main/url_128_rep0_leaf.json', lambda r: r['score_sha256'].update({'1': '0' * 64}))
        self.reject()

    def test_failed_exit(self):
        self.change('results/main/url_128_rep0_leaf.json', lambda r: r.update(exit_code=1))
        self.reject()

    def test_wrong_original_count(self):
        self.change('results/main/url_128_rep0_gama.json', lambda r: r['queries']['negative_tail'].update(fp=1))
        self.reject()

    def test_changed_source(self):
        p = self.root / 'src/ra6_worker14.py'
        original = p.read_bytes()
        self.addCleanup(p.write_bytes, original)
        p.write_bytes(original + b'\n# changed\n')
        self.reject()

    def test_full_check_requires_upstream_and_inputs(self):
        with self.assertRaises(FileNotFoundError):
            collect(self.root, with_inputs=True)


if __name__ == '__main__':
    unittest.main()
