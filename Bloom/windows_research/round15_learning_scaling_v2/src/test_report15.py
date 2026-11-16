"""Synthetic bookkeeping fixtures only; never used as experiment measurements."""
import json
import tempfile
import unittest
from pathlib import Path
from common15 import LENGTHS, digest, save, REPS, PILOT_L
from report15 import collect, render


class ArchiveChecks(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='ra15-report-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)/'windows_research/round15_learning_scaling_v2'
        root=self.root
        worker=root/'src/worker15.py';worker.parent.mkdir(parents=True);worker.write_text('# fixture, not executable experiment\n')
        source='windows_research/round15_learning_scaling_v2/src/worker15.py'
        manifest=dict(lengths=list(LENGTHS),reps=3,dataset='caida',budget_kib=256,
                      sources={source:digest(worker)},input_cache_hashes={},
                      stream=dict(n_pool=1000,prefix_sha256={str(L):'a'*64 for L in LENGTHS}))
        save(root/'plan/freeze.json',dict(candidate_count=180,sources=manifest['sources']))
        save(root/'results/manifest.json',manifest)
        save(root/'results/main/completion.json',dict(status='complete',workers=42,pairs=21,lengths=7,
             manifest_sha256=digest(root/'results/manifest.json')))
        save(root/'results/main/pair_checks.json',[dict(L=L,rep=r,matched_inputs_and_candidates=True) for L in LENGTHS for r in range(REPS)])
        grid=[[n,0. if n<14 else .01,0 if n<14 else 2000,0 if n<14 else 100] for n in range(180)]
        for L in LENGTHS:
            for rep in range(REPS):
                for m in ('ra6','replay'):
                    choice=dict(trees=1,frac=.01,cache_bytes=2000,used_bytes=250000,
                                member_false_negatives=0,verified_full_build=True,keys_sha256='b'*64)
                    r=dict(status='ok',exit_code=0,method=m,L=L,rep=rep,horizon=3*L,pilot=False,
                           dataset='caida',budget_kib=256,threads=1,numba_threads=1,thread_environment={str(i):'1' for i in range(5)},
                           candidates=180,built=5 if m=='ra6' else 180,worker_sha256=digest(worker),stream_sha256='a'*64,
                           pool_keys=1000,distinct_keys=1000,learning_trace_bytes=L*8,choice=choice,
                           selection_s=3.,count_s=1.,local_map_s=0.,predict_table_s=1. if m=='ra6' else 0.,
                           build_refine_s=1. if m=='ra6' else 0.,candidate_build_s=0. if m=='ra6' else 1.,
                           replay_s=0. if m=='ra6' else 1.,candidate_grid_sha256='c'*64,candidate_grid=grid,
                           candidate_query_visits=0 if m=='ra6' else 166*L,process_wall_s=5.,
                           learning_state_bytes=24000,count_state_bytes=16000,peak_rss_bytes=1000000)
                    if m=='replay':
                        r.update(cached_candidates=166,cutoff_candidates=0,learning_fp=100,
                                 replay_records=[dict(trees=t,frac=f,cache_bytes=cb,processed=L if cb else 0,cutoff=False) for t,f,cb,_ in grid])
                        choice['learning_fp_check']=100
                    path=root/f'results/main/L{L}_rep{rep}_{m}.json'
                    save(path,r);path.with_suffix('.log').write_text(f'COMPLETE {m} L={L} rep={rep}\n')
        save(root/'results/pilot/completion.json',dict(status='complete',workers=2))
        for m in ('ra6','replay'):
            save(root/f'results/pilot/L{PILOT_L}_rep0_{m}.json',dict(status='ok',pilot=True,choice=dict(canonical_ra6_check=True,no_cutoff_grid_check=True,full_pool_replay_check=True)))

    def change(self,mutate):
        p=self.root/'results/main/L1000000_rep0_replay.json'
        r=json.loads(p.read_text());mutate(r);save(p,r)

    def reject(self):
        with self.assertRaises((AssertionError,FileNotFoundError,KeyError)):collect(self.root)

    def test_complete_fixture(self):
        rows,summary,report=collect(self.root)
        self.assertEqual((len(rows),len(summary),report['workers']),(42,7,42))
        self.assertEqual(summary[0]['speedup_median'],1)
        self.assertIn('not by itself a different asymptotic class',render(rows,summary)['report.md'])

    def test_missing_endpoint(self):
        (self.root/'results/main/L100000000_rep2_ra6.json').unlink();self.reject()

    def test_failed_worker(self):
        self.change(lambda r:r.update(exit_code=1));self.reject()

    def test_preprocessing_omitted_from_total(self):
        self.change(lambda r:r.update(selection_s=2));self.reject()

    def test_incorrect_query_scan_total(self):
        self.change(lambda r:r.update(candidate_query_visits=1));self.reject()

    def test_changed_grid(self):
        self.change(lambda r:r.update(candidate_grid_sha256='d'*64));self.reject()

    def test_mismatched_stream(self):
        self.change(lambda r:r.update(stream_sha256='d'*64));self.reject()

    def test_extra_run(self):
        save(self.root/'results/main/L1000000_rep9_ra6.json',{});self.reject()


if __name__=='__main__':unittest.main()
