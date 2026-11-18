"""Offline archive regression checks with deliberate corruption of temporary copies."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from report20 import ROOT,collect,render


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='ra20-archive-')
        cls.bloom=Path(cls.temp.name);cls.root=cls.bloom/'windows_research'/ROOT.name
        record=json.loads((ROOT/'results/verification.json').read_text())
        freeze=json.loads((ROOT/'plan/freeze.json').read_text())
        paths=set(record['records'])|set(freeze['sources'])
        for rel in paths:
            dest=cls.bloom/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT.parents[1]/rel,dest)

    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()

    def change(self,fn):
        p=self.root/'results/main/caida_tcp_flow_index.json'
        original=p.read_bytes();self.addCleanup(p.write_bytes,original)
        row=json.loads(original);fn(row);p.write_text(json.dumps(row))

    def rejected(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):collect(self.root)

    def test_data_free_reproduction(self):
        rows,flat,summary,_=collect(self.root)
        self.assertEqual((len(rows),len(flat)),(192,576))
        for name,text in render(rows,flat,summary).items():
            self.assertEqual(text.encode(),(ROOT/'results'/name).read_bytes())

    def test_failed_job(self):
        self.change(lambda r:r.update(exit_code=1));self.rejected()

    def test_duplicate_case(self):
        self.change(lambda r:r['cases'].append(r['cases'][0]));self.rejected()

    def test_false_learning_guarantee(self):
        self.change(lambda r:r['cases'][0]['gate'].update(selected_learning_fp=10**9));self.rejected()

    def test_wrong_family_choice(self):
        self.change(lambda r:r['cases'][0]['gate'].update(family='learned'));self.rejected()

    def test_tail_not_selected_candidate(self):
        self.change(lambda r:r['cases'][0]['methods']['RA6-ZGate'].update(fp=0));self.rejected()

    def test_changed_reference(self):
        self.change(lambda r:r.update(round17_archive_sha256='0'*64));self.rejected()

    def test_changed_frozen_source(self):
        p=self.root/'src/guard20.py';old=p.read_bytes();self.addCleanup(p.write_bytes,old)
        p.write_bytes(old+b'\n# changed\n');self.rejected()

    def test_inputs_required_only_on_request(self):
        with self.assertRaises(FileNotFoundError):collect(self.root,with_inputs=True)


if __name__=='__main__':unittest.main()
