"""Complete-archive verification and arithmetic only; never runs a selection worker."""
import argparse
import csv
import io
import json
import math
from statistics import median
from common15 import ROOT, BLOOM, LENGTHS, REPS, PILOT_L, digest, save

PHASES = ('selection_s', 'count_s', 'local_map_s', 'predict_table_s', 'build_refine_s', 'candidate_build_s', 'replay_s')


def collect(root=ROOT, with_inputs=False):
    assert __debug__, 'Assertions must be enabled'
    bloom = root.parents[1]
    manifest = json.loads((root/'results/manifest.json').read_text())
    done = json.loads((root/'results/main/completion.json').read_text())
    assert done == dict(status='complete',workers=42,pairs=21,lengths=7,manifest_sha256=digest(root/'results/manifest.json'))
    assert manifest['lengths']==list(LENGTHS) and manifest['reps']==3
    assert manifest['dataset']=='caida' and manifest['budget_kib']==256
    freeze=json.loads((root/'plan/freeze.json').read_text())
    assert freeze['candidate_count']==180 and freeze['sources']==manifest['sources']
    checked={}
    for rel,want in manifest['sources'].items():
        assert digest(bloom/rel)==want,rel
        checked[rel]=want
    if with_inputs:
        for rel,want in manifest['input_cache_hashes'].items():
            assert digest(bloom/rel)==want,rel
            checked[rel]=want
        assert digest(root/'inputs/learning.npy')==manifest['stream']['file_sha256']
    expected={f'L{L}_rep{rep}_{method}' for L in LENGTHS for rep in range(REPS) for method in ('ra6','replay')}
    for ext in ('.json','.log'):
        assert {p.stem for p in (root/'results/main').glob(f'L*_rep*_*{ext}')}==expected,ext
    raw=[];summaries=[];grid=None
    for L in LENGTHS:
        methods={m:[] for m in ('ra6','replay')}
        for rep in range(REPS):
            pair={}
            for method in methods:
                p=root/f'results/main/L{L}_rep{rep}_{method}.json'
                r=json.loads(p.read_text());checked[str(p.relative_to(bloom))]=digest(p)
                assert r['status']=='ok' and r['exit_code']==0 and r['method']==method
                assert (r['L'],r['rep'],r['horizon'])==(L,rep,3*L) and not r['pilot']
                assert r['dataset']=='caida' and r['budget_kib']==256 and r['threads']==r['numba_threads']==1
                assert len(r['thread_environment'])==5 and set(r['thread_environment'].values())=={'1'}
                assert r['candidates']==180 and r['built']==(5 if method=='ra6' else 180)
                assert r['worker_sha256']==manifest['sources'][str((root/'src/worker15.py').relative_to(bloom))]
                assert r['stream_sha256']==manifest['stream']['prefix_sha256'][str(L)]
                assert r['pool_keys']==manifest['stream']['n_pool'] and 0<r['distinct_keys']<=min(L,r['pool_keys'])
                assert r['learning_trace_bytes']==L*8
                assert r['choice']['member_false_negatives']==0 and r['choice']['verified_full_build']
                assert r['choice']['cache_bytes']<=r['choice']['used_bytes']<=256*1024
                for k in PHASES:assert math.isfinite(r[k]) and r[k]>=0,(p,k)
                assert r['selection_s']>0 and r['selection_s']<r['process_wall_s']
                assert math.isclose(r['selection_s'],sum(r[k] for k in PHASES[1:]),rel_tol=1e-10,abs_tol=1e-8)
                if grid is None:grid=r['candidate_grid_sha256']
                assert r['candidate_grid_sha256']==grid and len(r['candidate_grid'])==180
                if method=='replay':
                    records=r['replay_records'];assert len(records)==180
                    assert {(x['trees'],x['frac'],x['cache_bytes']) for x in records}=={tuple(x[:3]) for x in r['candidate_grid']}
                    assert r['cached_candidates']==166 and r['cutoff_candidates']==sum(x['cutoff'] for x in records)
                    assert r['candidate_query_visits']==sum(x['processed'] for x in records)
                    assert 0<r['candidate_query_visits']<=166*L
                    assert all(0<=x['processed']<=L for x in records)
                    assert r['learning_fp']==r['choice']['learning_fp_check']
                else:assert r['candidate_query_visits']==0
                log=p.with_suffix('.log');text=log.read_text()
                assert 'Traceback' not in text and f'COMPLETE {method} L={L} rep={rep}' in text
                checked[str(log.relative_to(bloom))]=digest(log)
                methods[method].append(r);pair[method]=r
                raw.append({k:r[k] for k in ('method','L','rep','distinct_keys','pool_keys',*PHASES,'candidates','built',
                                            'candidate_query_visits','learning_trace_bytes','learning_state_bytes',
                                            'count_state_bytes','peak_rss_bytes','process_wall_s')})
            for key in ('candidate_grid_sha256','stream_sha256','distinct_keys'):
                assert pair['ra6'][key]==pair['replay'][key],key
            assert pair['ra6']['choice']['keys_sha256']==pair['replay']['choice']['keys_sha256']
        # Fixed workload, not random seeds: selected configurations/counts must replicate.
        for method,rr in methods.items():
            for row in rr[1:]:
                assert row['choice']==rr[0]['choice'],(L,method,'non-deterministic choice')
        ratios=[b['selection_s']/a['selection_s'] for a,b in zip(methods['ra6'],methods['replay'])]
        gaps=[b['selection_s']-a['selection_s'] for a,b in zip(methods['ra6'],methods['replay'])]
        summary=dict(L=L,distinct_keys=methods['ra6'][0]['distinct_keys'],
                     pool_fraction=methods['ra6'][0]['distinct_keys']/methods['ra6'][0]['pool_keys'],
                     speedup_median=median(ratios),speedup_range=[min(ratios),max(ratios)],speedup_all=ratios,
                     gap_median_s=median(gaps),methods={})
        for method,rr in methods.items():
            summary['methods'][method]={k:dict(median=median(r[k] for r in rr),min=min(r[k] for r in rr),max=max(r[k] for r in rr))
                                        for k in (*PHASES,'peak_rss_bytes','candidate_query_visits','learning_state_bytes')}
            summary['methods'][method]['choice']=rr[0]['choice']
        summaries.append(summary)
    checks=json.loads((root/'results/main/pair_checks.json').read_text())
    assert checks==[dict(L=L,rep=rep,matched_inputs_and_candidates=True) for L in LENGTHS for rep in range(REPS)]
    pilot=json.loads((root/'results/pilot/completion.json').read_text())
    assert pilot==dict(status='complete',workers=2)
    for method in ('ra6','replay'):
        r=json.loads((root/f'results/pilot/L{PILOT_L}_rep0_{method}.json').read_text())
        assert r['status']=='ok' and r['pilot']
        assert r['choice']['canonical_ra6_check'] if method=='ra6' else (r['choice']['no_cutoff_grid_check'] and r['choice']['full_pool_replay_check'])
    return raw,summaries,dict(status='verified',workers=42,pairs=21,checked_raw_inputs=with_inputs,sources=checked)


def render(raw,summary):
    lines=['# Learning-period scaling: 1M to 100M queries','',
           'CAIDA,256KiB,Zipf1.0,180 feasible candidates (14×13 nominal grid). '
           'Each point contains three fresh single-threaded runs; no pilot observations or extrapolated times are plotted. '
           'Both selection timers include learning-dependent counting; Replay additionally includes local-key mapping. '
           'Trained models, scores and length-independent segment arrays are prepared before either timer.','',
           '| Learning queries | Distinct keys | Pool seen | RA-PLBF/RA6 s | Replay s | Paired speedup | Paired time gap s |',
           '|---|---:|---:|---:|---:|---:|---:|']
    for s in summary:
        lines.append(f"| {s['L']:,} | {s['distinct_keys']:,} | {s['pool_fraction']:.1%} | {s['methods']['ra6']['selection_s']['median']:.3f} | {s['methods']['replay']['selection_s']['median']:.3f} | {s['speedup_median']:.2f}× | {s['gap_median_s']:.3f} |")
    lines+=['','## Phase medians (do not add medians to obtain the total median)','',
            '| L | RA count s | RA prediction/DP s | RA top-5 build/refine s | Replay count s | Replay mapping s | Replay builds s | Replay ordered scans s | Replay scan visits / L |',
            '|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for s in summary:
        a,b=s['methods']['ra6'],s['methods']['replay']
        vals=[a['count_s']['median'],a['predict_table_s']['median'],a['build_refine_s']['median'],
              b['count_s']['median'],b['local_map_s']['median'],b['candidate_build_s']['median'],b['replay_s']['median'],
              b['candidate_query_visits']['median']/s['L']]
        lines.append(f"| {s['L']:,} | "+' | '.join(f'{v:.3f}' for v in vals)+' |')
    lo,hi=summary[0],summary[-1]
    growth={m:hi['methods'][m]['selection_s']['median']/lo['methods'][m]['selection_s']['median'] for m in ('ra6','replay')}
    monotone=all(a['speedup_median']<=b['speedup_median'] for a,b in zip(summary,summary[1:]))
    lines+=['','## What this establishes—and what it does not','',
            f"- Over the 100× increase in L, RA6's total selection median grows {growth['ra6']:.2f}× and Replay's {growth['replay']:.2f}×. The endpoint paired-speedup medians are {lo['speedup_median']:.2f}× and {hi['speedup_median']:.2f}×. Monotonically increasing across all seven medians: **{'yes' if monotone else 'no'}**.",
            '- An increasing seconds gap is not by itself a different asymptotic class. These are measurements for one finite pool, workload, budget and fixed candidate set, not a proof as L approaches infinity.',
            '- RA6 counts once per selection, builds populations per tree prefix, scores every candidate and builds five candidates. It avoids repeating ordered learning traces for each candidate; it is not independent of L, distinct-key count D, or candidate count C.',
            '- The frozen counter uses sort-based np.unique with return_counts, not a proved O(L) streaming counter. Both timers include their counting. Replay also maps L indices; the table separately exposes mapping and actual candidate scan costs.',
            '- Replay retains exact incumbent early stopping and zero-cache weighted counting. Its relevant scan term is the sum of actual candidate visits (bounded above by 166L here), not an assumed 180L. No scans were disabled or inflated to produce a favorable ratio.',
            '- Fixed-pool coverage and distinct keys are reported because repetition increases as the pool saturates. Per-tree population work and top-five refinement still depend on these statistics. Dependence on candidate count cannot be identified by this fixed-C experiment alone.',
            '- H=3L is the predicted deployment horizon, but no 300M-query evaluation tail was allocated. Choice validity, all-member acceptance and selected-BF equality are checked outside timing. Learning FP counts do not establish held-out prediction quality.',
            '- This is selection cost with cached scores, not full training-to-ready time or a comparison with the authors\' original Gama implementation. Early rounds and paper files are unchanged.',
            '- Min–max intervals describe three timing repetitions of the same nested stream, not independent workload confidence intervals. No unfavorable repeat is dropped. Whole-process RSS includes shared model setup and post-timing checks.',
            '- The initial launcher generated the stream but failed on an unavailable optional threadpoolctl import before a selection measurement. v2 reuses the identical stream and removes that instrumentation dependency. Failed logs and frozen sources remain in the previous directory.']
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=list(raw[0]));w.writeheader();w.writerows(raw)
    return {'report.md':'\n'.join(lines)+'\n','timing_rows.csv':buf.getvalue(),'summary.json':json.dumps(summary,indent=2)+'\n'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    rows,summary,verification=collect(with_inputs=a.inputs)
    for name,text in render(rows,summary).items():
        path=ROOT/'results'/name
        if a.verify_only:assert path.read_bytes()==text.encode(),name
        else:path.write_bytes(text.encode())
    if not a.verify_only:save(ROOT/'results/verification.json',verification)
    print('PASS: 42 complete workers, 21 matched pairs, all seven lengths and timing arithmetic verified')
