"""Standard-library replay of the audit report from an input-data-free copy."""
import contextlib
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
import report18


class AuditArchiveTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(prefix='gt-audit-copy-')
        cls.bloom=Path(cls.tmp.name)
        cls.original_root=report18.ROOT
        cls.root=cls.bloom/'windows_research/round18_gt_audit'
        sourcepaths=set()
        for ds in report18.DATASETS:
            obj=json.loads((cls.original_root/f'results/{ds}.json').read_text())
            sourcepaths.update(obj['sources'])
        for rel in sourcepaths:
            p=cls.bloom/rel;p.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(cls.original_root.parents[1]/rel,p)
        shutil.copytree(cls.original_root/'results',cls.root/'results')

    @classmethod
    def tearDownClass(cls):cls.tmp.cleanup()

    def setUp(self):
        report18.ROOT=self.root
        self.addCleanup(setattr,report18,'ROOT',self.original_root)

    def run_report(self):
        with contextlib.redirect_stdout(io.StringIO()):report18.main(verify_only=True)

    def mutate(self,rel,fn):
        p=self.root/rel;b=p.read_bytes();self.addCleanup(p.write_bytes,b)
        x=json.loads(b);fn(x);p.write_text(json.dumps(x))

    def reject(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):self.run_report()

    def test_complete_data_free_reconstruction(self):self.run_report()

    def test_missing_dataset(self):
        p=self.root/'results/cod.json';b=p.read_bytes();self.addCleanup(p.write_bytes,b);p.unlink();self.reject()

    def test_duplicate_case(self):
        self.mutate('results/cod.json',lambda x:x['cases'].append(x['cases'][0]));self.reject()

    def test_wrong_affected_query_count(self):
        def alter(x):
            row=next(s for s in x['streams'] if s['gap_c'] and not s['all_singletons'])
            row['gap_learning_queries']=0
        self.mutate('results/cod.json',alter);self.reject()

    def test_changed_statistic_hash(self):
        self.mutate('results/cod.json',lambda x:x['cases'][0].update(original_rate_sha256='0'*64));self.reject()

    def test_summary_not_trusted(self):
        self.mutate('results/summary.json',lambda x:x['main'].update(non_singleton_gap=0));self.reject()

    def test_source_not_silently_changed(self):
        p=self.root/'src/audit18.py';b=p.read_bytes();self.addCleanup(p.write_bytes,b)
        p.write_bytes(b+b'\n# changed\n');self.reject()


if __name__=='__main__':unittest.main()
