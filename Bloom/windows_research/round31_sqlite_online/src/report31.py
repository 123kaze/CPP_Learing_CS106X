"""Report only completed, exact-feedback experiments; no selection from timing outcomes."""
from pathlib import Path
import sys,json,csv,hashlib
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
SETTINGS={'cod':1024,'url':128,'caida':256,'shalla':1024,'caida_flow':24,'mawi2020_flow':24,'mawi2021_flow':24,'mawi2022_flow':24}


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['timing_records']==312
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    rows=[];medians=[];files={}
    for ds,kib in SETTINGS.items():
        path=ROOT/f'results/{ds}.json';d=json.loads(path.read_text());files[path.name]=sha(path)
        assert d['status']=='complete' and d['native_threads']==1 and d['queries']==200000
        assert d['freeze_sha256']==sha(ROOT/'plan/freeze.json') and d['preparation']['gt19_statistics_equal_original']
        methods={'NoFilter',*d['methods']};assert len(methods)==(6 if ds.endswith('_flow') else 7)
        assert {(r['backend'],r['rep'],r['method']) for r in d['timings']}=={(b,n,m) for b in ('file','memory') for n in range(3) for m in methods}
        for m,r in d['methods'].items():
            assert r['all_members_native_fn']==0 and r['all_pool_flags_equal']
            assert r['compact_online_buffer_bytes']<=r['original_reserved_bytes']<=kib*1024
        for r in d['timings']:
            assert r['member_fn']==0 and r['full_mask_equal_reference'] and r['packed_cache_equal_reference']
            assert r['members_found']==d['member_queries'] and r['backend_calls']==r['fp']+r['members_found']
            assert r['backend_calls']+r['cache_hits']+r['filter_rejects']==200000
            assert r['ns_per_query']==r['elapsed_ns']/200000
            if r['method']!='NoFilter':
                ref=d['methods'][r['method']]
                assert r['accepted_mask_sha256']==ref['expected_mask_sha256'] and r['final_cache_sha256']==ref['expected_cache_sha256']
                for k1,k2 in [('fp','expected_fp'),('backend_calls','expected_backend_calls'),('members_found','expected_members_found'),('cache_hits','expected_cache_hits')]:assert r[k1]==ref[k2]
            rows.append(dict(dataset=ds,budget_kib=kib,**r))
        for backend in ('file','memory'):
            vals={m:median(r['ns_per_query'] for r in d['timings'] if r['method']==m and r['backend']==backend) for m in methods}
            for method,value in vals.items():
                ref=next(r for r in d['timings'] if r['backend']==backend and r['method']==method)
                medians.append(dict(dataset=ds,budget_kib=kib,backend=backend,method=method,median_us=value/1000,
                                    ratio_to_NoFilter=value/vals['NoFilter'],ratio_to_BF_cache=value/vals['BF+Cache'],
                                    ratio_to_Gama=value/vals['Gama'],backend_calls=ref['backend_calls'],fp=ref['fp'],members_found=ref['members_found']))
    assert len(rows)==312 and len(medians)==104
    for name,data in [('timings.csv',rows),('medians.csv',medians)]:
        with (ROOT/'results'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    text=['# SQLite: per-request SQL-confirmed negative feedback','',
          '**Completed:**8settings,2backends,3repetitions,312timings. All accepted masks and final packed cache states match the independent batched-label reference. Every online insertion follows an actual SQL result ofNone.','',
          'This is a Python scalar API orchestration benchmark with Numba filter probes and real sqlite3 SELECTs. It includes scalar dispatch, feedback, safe-prefix search and result-mask accounting. Features/hashes are prepared outside the timer. It is NOT native-C++ latency, p99, cold disk or network-backend performance. The old batched e789 timing and these online timings are different execution paths; do not interpret their ratio as a hardware-independent slowdown.','',
          '## Median time (microseconds/query); every repeat retained','',
          '| Dataset | Backend | NoFilter | BF+Cache | Gama | Replay | RA-PLBF | RA/NoFilter | RA/BF+Cache |','|---|---|---:|---:|---:|---:|---:|---:|---:|']
    wins_n=wins_b=wins_g=0
    for ds in SETTINGS:
        for backend in ('file','memory'):
            rr={r['method']:r for r in medians if r['dataset']==ds and r['backend']==backend};ra=rr['RA6']
            wins_n+=ra['ratio_to_NoFilter']<1;wins_b+=ra['ratio_to_BF_cache']<1;wins_g+=ra['ratio_to_Gama']<1
            text.append(f'| {ds} | {backend} | '+ ' | '.join(f'{rr[m]["median_us"]:.3f}' for m in ('NoFilter','BF+Cache','Gama','LearnGrid','RA6'))+f' | {ra["ratio_to_NoFilter"]:.3f} | {ra["ratio_to_BF_cache"]:.3f} |')
    text+=['','## Verification and limits','',
           f'- RA-PLBF has lower median time in{wins_n}/16backend-settings versusNoFilter,{wins_b}/16versusBF+Cache,{wins_g}/16versusGama. This is descriptive, not a significance claim from16independent datasets.',
           '- Same200000requests as archived e789 in each setting, RNG8member mixing. Learned-method selections, full-tailFP and archived backend-call/member-found counts reproduce. GT19statistics are explicitly identical to the original on these timed inputs.',
           '- Every online run checks the entire backend-call mask and exact packed final cache bytes against a separately labeled simulation. All members are queried through the new compact native path and all negative-pool flags match before timing; final cache member-hit checks are zero.',
           '- FastPLBF48 is infeasible on the four24KiBtraces and is listed as such, not replaced. The complete table includes it and Gama+10%where feasible, even though the compact headline table above has five methods.',
           '- Learned online routing uses4raw-score boundaries instead of legacy1000-segment expanded arrays. All-key equivalence is checked. Actual online model/BF/layout/cache bytes and original conservative reserved bytes are both recorded; no saved metadata bytes are retuned into extraBFbits.',
           '- Backend member-hash index remains external8*nbytes plus header. Safe-prefix computation is inside online feedback timing. Backend database pages, creation/warmup time, prepared-feature memory and peakRSS are distinct from Filter Budget.',
           '- SQLite file mode is warmed and fits local-memory conditions; not cold storage. Methods rotate order over3repetitions; there is no retrospective best-repeat picking. Exact-feedback correctness does not remove all runtime/order/environment effects.',
           '- These results replace neither the frozen FP study nor the originalMAWI24holdout; they are post-hoc execution-path validation. No paper patch is applied automatically.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    summary=dict(status='verified',settings=8,timing_records=312,all_online_masks_equal=True,all_final_caches_equal=True,member_fn=0,
                 median_time_wins_vs_NoFilter=int(wins_n),median_time_wins_vs_BF_cache=int(wins_b),median_time_wins_vs_Gama=int(wins_g),backend_settings=16,source_files=files)
    (ROOT/'results/verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
