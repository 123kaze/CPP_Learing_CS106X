"""Read-only archive verification without raw datasets; reject altered records."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from report22 import ROOT,collect,render


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='kl22-archive-')
        cls.bloom=Path(cls.tmp.name);cls.root=cls.bloom/'windows_research'/ROOT.name
        freeze=json.loads((ROOT/'plan/freeze.json').read_text())
        records=json.loads((ROOT/'results/verification.json').read_text())
        paths=set(freeze['source_sha256'])|set(records['records'])
        for rel in paths:
            dst=cls.bloom/rel;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(ROOT.parents[1]/rel,dst)
    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()
    def changed(self,relative,fn):
        p=self.root/relative;b=p.read_bytes();self.addCleanup(p.write_bytes,b)
        obj=json.loads(b);fn(obj);p.write_text(json.dumps(obj))
    def rejected(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):collect(self.root)
    def test_data_free_reconstruction(self):
        data=collect(self.root)
        self.assertEqual(len(data[0]),13)
        self.assertEqual(data[3]['static_candidates'],141)
        for name,text in render(*data[:4]).items():self.assertEqual(text.encode(),(ROOT/'results'/name).read_bytes())
    def test_missing_matrix_dataset(self):
        p=self.root/'results/matrix/caida.json';b=p.read_bytes();self.addCleanup(p.write_bytes,b);p.unlink();self.rejected()
    def test_changed_candidate_record(self):
        self.changed('results/matrix/caida.json',lambda r:r['cases'][0]['heuristic'].update(trees=0));self.rejected()
    def test_wrong_smoke_reference(self):
        self.changed('results/matrix/completion.json',lambda r:r['smoke_reference'].update(sha256='0'*64));self.rejected()
    def test_changed_frozen_math(self):
        p=self.root/'src/math22.py';b=p.read_bytes();self.addCleanup(p.write_bytes,b);p.write_bytes(b+b'\n#changed\n');self.rejected()
    def test_incomplete_flag(self):
        self.changed('results/matrix/completion.json',lambda r:r.update(status='running'));self.rejected()
    def test_actual_inputs_not_silently_skipped(self):
        with self.assertRaises(FileNotFoundError):collect(self.root,with_inputs=True)


if __name__=='__main__':unittest.main()
