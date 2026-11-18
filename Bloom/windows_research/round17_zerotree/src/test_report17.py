"""Verify complete archived cases from a raw-data-free copy and reject corruption."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from report17 import ROOT,collect,render,diagnostics


class ArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='ra17-archive-')
        cls.bloom=Path(cls.tmp.name);cls.root=cls.bloom/'windows_research'/ROOT.name
        record=json.loads((ROOT/'results/verification.json').read_text())
        for rel in record['sources']:
            dest=cls.bloom/rel;dest.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(ROOT.parents[1]/rel,dest)

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def mutate(self,fn):
        p=self.root/'results/main/caida_tcp_flow_index.json'
        original=p.read_bytes();self.addCleanup(p.write_bytes,original)
        row=json.loads(original);fn(row);p.write_text(json.dumps(row))

    def reject(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):collect(self.root)

    def test_complete_data_free_copy(self):
        rows,flat,stats,_=collect(self.root)
        self.assertEqual((len(rows),len(flat)),(192,1536))
        for name,text in render(rows,flat,stats).items():self.assertEqual(text.encode(),(ROOT/'results'/name).read_bytes())
        d=diagnostics(rows)
        self.assertEqual([len(x) for x in d['index']['remaining_tcp_losses'].values()],[5,2,1])
        self.assertEqual([len(x) for x in d['fp64']['remaining_tcp_losses'].values()],[4,2,2])

    def test_missing_job(self):
        p=self.root/'results/main/caida_tcp_flow_index.json';original=p.read_bytes()
        self.addCleanup(p.write_bytes,original);p.unlink();self.reject()

    def test_failed_job(self):
        self.mutate(lambda r:r.update(exit_code=1));self.reject()

    def test_duplicate_case(self):
        self.mutate(lambda r:r['results'].append(r['results'][0]));self.reject()

    def test_zero_charged_model_bytes(self):
        self.mutate(lambda r:r['results'][0]['methods']['RA6-Z'].update(model_bytes=1));self.reject()

    def test_changed_archived_reference(self):
        self.mutate(lambda r:r['results'][0]['methods']['RA6'].update(fp=0,fpr=0.));self.reject()

    def test_bad_expanded_training_objective(self):
        self.mutate(lambda r:r['results'][0].update(expanded_replay_learn_fp=10**12));self.reject()

    def test_no_native_validation(self):
        self.mutate(lambda r:r['results'][0]['methods']['RA6-Z'].update(native_zero_checks=False));self.reject()

    def test_frozen_source_change(self):
        p=self.root/'src/zero17.py';original=p.read_bytes();self.addCleanup(p.write_bytes,original)
        p.write_bytes(original+b'\n# changed\n');self.reject()

    def test_raw_inputs_required_when_requested(self):
        with self.assertRaises(FileNotFoundError):collect(self.root,with_inputs=True)


if __name__=='__main__':unittest.main()
