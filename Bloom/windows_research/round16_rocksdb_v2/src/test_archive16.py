"""Offline, data-free archive verification and deliberate corruption tests."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from report16 import ROOT,collect,render


class ArchiveChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ra16-archive-')
        cls.bloom=Path(cls.tmp.name);cls.root=cls.bloom/'windows_research'/ROOT.name
        record=json.loads((ROOT/'results/verification.json').read_text())
        for rel in record['sources']:
            dest=cls.bloom/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT.parents[1]/rel,dest)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def change(self,rel,fn):
        p=self.root/rel;original=p.read_bytes();self.addCleanup(p.write_bytes,original)
        r=json.loads(original);fn(r);p.write_text(json.dumps(r))

    def reject(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):collect(self.root)

    def test_data_free_reproduction(self):
        raw,tables,_=collect(self.root)
        self.assertEqual((len(raw),len(tables)),(60,20))
        for name,text in render(raw,tables).items():self.assertEqual(text.encode(),(ROOT/'results'/name).read_bytes())

    def test_missing_run(self):
        p=self.root/'results/main/zipf_fit_rep0_RA6.json'
        original=p.read_bytes();self.addCleanup(p.write_bytes,original);p.unlink();self.reject()

    def test_failed_worker(self):
        self.change('results/main/zipf_fit_rep0_RA6.json',lambda r:r.update(exit_code=1));self.reject()

    def test_false_claim_of_enabled_bloom(self):
        self.change('results/main/zipf_fit_rep0_Direct.json',lambda r:r['configuration_check'].update(bloom_useful_of_2000_misses=0));self.reject()

    def test_wrong_get_count(self):
        self.change('results/main/zipf_fit_rep0_RA6.json',lambda r:r.update(db_calls=1));self.reject()

    def test_latency_file_changed(self):
        p=self.root/'results/main/zipf_fit_rep0_RA6.latency.npz'
        original=p.read_bytes();self.addCleanup(p.write_bytes,original);p.write_bytes(original+b'changed');self.reject()

    def test_source_changed(self):
        p=self.root/'src/query16.py'
        original=p.read_bytes();self.addCleanup(p.write_bytes,original);p.write_bytes(original+b'\n# changed\n');self.reject()

    def test_inputs_not_silently_skipped(self):
        with self.assertRaises(FileNotFoundError):collect(self.root,with_inputs=True)


if __name__=='__main__':unittest.main()
