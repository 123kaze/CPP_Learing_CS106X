"""Reconstruct zero-tree effectiveness comparisons only from a complete archive."""
import argparse
import csv
import io
import json
import math
from statistics import median
from common17 import ROOT,WR,BLOOM,TCP,DATASETS,METHODS,cases,digest,save


def ratios(rows,method,reference):
    values=[(r['methods'][method]['fp']+1)/(r['methods'][reference]['fp']+1) for r in rows]
    return dict(cases=len(rows),median=median(values),minimum=min(values),maximum=max(values),
                wins=sum(r['methods'][method]['fp']<r['methods'][reference]['fp'] for r in rows),
                ties=sum(r['methods'][method]['fp']==r['methods'][reference]['fp'] for r in rows),
                losses=sum(r['methods'][method]['fp']>r['methods'][reference]['fp'] for r in rows),
                zero_selected=sum(r['methods'][method]['trees']==0 for r in rows))


def collect(root=ROOT,with_inputs=False):
    assert __debug__,'Verification requires assertions'
    bloom=root.parents[1];wr=root.parent;files={}
    def load(p):
        files[str(p.relative_to(bloom))]=digest(p)
        return json.loads(p.read_text())
    manifest=load(root/'results/manifest.json');freeze=load(root/'plan/freeze.json')
    assert manifest['freeze']==freeze and manifest['methods']==list(METHODS) and manifest['expected_cases']==192
    assert manifest['cases']==json.loads(json.dumps({ds:cases(ds) for ds in DATASETS}))
    done=load(root/'results/main/completion.json')
    assert done==dict(status='complete',jobs=16,cases=192,method_rows=1536,manifest_sha256=digest(root/'results/manifest.json'))
    for rel,h in freeze['sources'].items():
        assert digest(bloom/rel)==h,rel
        files[rel]=h
    if with_inputs:
        for rel,h in freeze['inputs'].items():assert digest(bloom/rel)==h,rel
    refpath=wr/'round13_complete/results/combined_baseline_rows.csv'
    assert digest(refpath)==freeze['inputs'][str(refpath.relative_to(bloom))]
    with refpath.open() as f:refs={(r['dataset'],r['cache'],int(r['budget_kib']),r['workload'],int(r['seed'])):r for r in csv.DictReader(f)}
    files[str(refpath.relative_to(bloom))]=digest(refpath)
    names={f'{ds}_{mode}' for ds in DATASETS for mode in ('index','fp64')}
    for ext in ('.json','.log'):
        actual={p.stem for p in (root/'results/main').glob('*'+ext) if p.stem not in ('progress','completion')}
        assert actual==names,(ext,actual^names)
    allrows=[];flat=[]
    for ds in DATASETS:
        for mode in ('index','fp64'):
            p=root/f'results/main/{ds}_{mode}.json';r=load(p)
            assert r['status']=='ok' and r['exit_code']==0 and not r['pilot']
            assert (r['dataset'],r['cache'])==(ds,mode)
            assert len(r['results'])==len(cases(ds))
            assert {(x['budget_kib'],x['workload'],x['seed'],x['cohort']) for x in r['results']}==set(cases(ds))
            log=p.with_suffix('.log');text=log.read_text();files[str(log.relative_to(bloom))]=digest(log)
            assert 'Traceback' not in text and f'COMPLETE {ds} {mode}:' in text
            for c in r['results']:
                assert c['dataset']==ds and c['cache']==mode
                assert set(c['methods'])==set(METHODS)
                info=c['zero_info'];assert info['built']==5 and info['zero_candidates']==13
                assert info['candidates']==info['learned_candidates']+13 and len(info['shortlist'])==5
                assert info['rank'] in range(5)
                selected=min(info['shortlist'],key=lambda x:(x['refined_pred'],x['rank']))
                assert (selected['rank'],selected['trees'],selected['frac'],selected['refined_pred'])==(info['rank'],info['trees'],info['frac'],info['predicted_fp'])
                assert c['expanded_replay_learn_fp']<=min(c['old_replay_learn_fp'],c['bf_replay_learn_fp'])
                ref=refs[ds,mode,c['budget_kib'],c['workload'],c['seed']]
                assert c['base_stream_sha256']==ref['base_stream_sha256'] and c['tail_len']==int(ref['tail_len'])
                for method,m in c['methods'].items():
                    assert type(m['fp']) is int and 0<=m['fp']<=c['tail_len']
                    assert m['member_checks_passed'] and m['total_bytes']<=c['budget_kib']*1024
                    assert 0<=m['cache_bytes']<=m['total_bytes'] and m['model_bytes']>=0
                    assert math.isclose(m['fpr'],m['fp']/c['tail_len'],rel_tol=1e-12,abs_tol=1e-15)
                    assert m['select_s']>=0 and math.isfinite(m['select_s'])
                    if m['trees']==0:assert m['model_bytes']==0 and m['metadata_bytes']==32 and m['native_zero_checks']
                    if method in ('RA6','Gama','BF','BF+ReplayCache','Replay'):
                        key={'RA6':'ra_fp','Gama':'gama_fp','BF':'bf_fp','BF+ReplayCache':'bfcache_fp','Replay':'replay_fp'}[method]
                        assert m['matches_round13_archive'] and m['fp']==int(ref[key])
                    flat.append(dict(dataset=ds,cache=mode,budget_kib=c['budget_kib'],workload=c['workload'],seed=c['seed'],
                                     cohort=c['cohort'],method=method,tail_len=c['tail_len'],**m))
                z=c['methods']['RA6-Z'];assert (z['trees'],z['frac'])==(info['trees'],info['frac'])
                assert c['methods']['Zero-Predict']['trees']==0
                allrows.append(c)
    assert len(allrows)==192 and len(flat)==1536
    stats={}
    for mode in ('index','fp64'):
        for cohort in ('weak_tcp','model_control','fresh_adversarial'):
            rows=[r for r in allrows if r['cache']==mode and r['cohort']==cohort]
            assert len(rows)==(16 if cohort=='weak_tcp' else 40)
            for method,reference in (('RA6-Z','BF+ReplayCache'),('RA6-Z','RA6'),('RA6-Z','Replay+Z'),
                                     ('RA6','BF+ReplayCache'),('Zero-Predict','BF+ReplayCache')):
                stats[f'{mode}/{cohort}/{method}/{reference}']=ratios(rows,method,reference)
    return allrows,flat,stats,dict(status='verified',cases=192,method_rows=1536,checked_raw_inputs=with_inputs,sources=files)


def diagnostics(rows):
    result={}
    for mode in ('index','fp64'):
        weak=[r for r in rows if r['cache']==mode and r['cohort']=='weak_tcp']
        buckets={'no_zero_in_shortlist':[],'learned_wins_refinement':[],'zero_fraction_differs_from_replay':[]}
        for r in weak:
            z=r['methods']['RA6-Z'];bf=r['methods']['BF+ReplayCache']
            if z['fp']<=bf['fp']:continue
            info=r['zero_info']
            if not any(x['trees']==0 for x in info['shortlist']):tag='no_zero_in_shortlist'
            elif z['trees']>0:tag='learned_wins_refinement'
            else:
                assert z['frac']!=bf['frac']
                tag='zero_fraction_differs_from_replay'
            buckets[tag].append(dict(dataset=r['dataset'],budget_kib=r['budget_kib'],zero_min_stage1_rank=info['zero_min_stage1_rank'],
                                     new_fp=z['fp'],bf_replay_fp=bf['fp'],zero_only_fp=r['methods']['Zero-Predict']['fp']))
        result[mode]={'remaining_tcp_losses':buckets}
        for cohort in ('model_control','fresh_adversarial'):
            sub=[r for r in rows if r['cache']==mode and r['cohort']==cohort]
            result[mode][cohort]=dict(cases=len(sub),zero_in_shortlist=sum(any(x['trees']==0 for x in r['zero_info']['shortlist']) for r in sub),
                  unchanged_from_ra6=sum(all(r['methods']['RA6-Z'][k]==r['methods']['RA6'][k] for k in ('trees','frac','cache_bytes','static_flags_sha256','fp')) for r in sub))
    return result


def render(cases_,flat,stats):
    lines=['# RA6-Z: adding physically accounted zero-tree candidates','',
           '192 post-hoc cases, two cache formats, eight methods. The original learned path is frozen. '
           'New RA6-Z merges13 zero-tree candidates into the global top-five predictive shortlist, then uses the same actual-bucket refinement. '
           'Selection sees learning statistics, never evaluation-tail outcomes. All five original reference methods reproduce round13 exactly.','',
           'Ratios are per-case `(FP_method+1)/(FP_reference+1)` before taking medians. All cases are retained, including low counts. '
           'Zero-selected counts refer to the numerator method. These cases share datasets/models and are not independent statistical samples.','',
           '| Cache | Cohort | Method / reference | Cases | Zero selected | Median FP ratio | Win/tie/loss | Worst ratio |',
           '|---|---|---|---:|---:|---:|---|---:|']
    for key,s in stats.items():
        mode,cohort,m,ref=key.split('/')
        lines.append(f"| {mode} | {cohort} | {m} / {ref} | {s['cases']} | {s['zero_selected']} | {s['median']:.4f} | {s['wins']}/{s['ties']}/{s['losses']} | {s['maximum']:.4f} |")
    lines+=['','## All TCP-only settings','',
            '| Cache | Dataset | KiB | Original RA6 FP | BF+ReplayCache FP | RA6-Z FP | RA6-Z trees | Cache fraction | Expanded Replay FP |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in cases_:
        if r['cohort']!='weak_tcp':continue
        m=r['methods'];z=m['RA6-Z']
        lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {m['RA6']['fp']} | {m['BF+ReplayCache']['fp']} | {z['fp']} | {z['trees']} | {z['frac']} | {m['Replay+Z']['fp']} |")
    lines+=['','## Remaining failures and regressions','',
            '| Cache | Dataset | KiB | Workload | Seed | New FP | Old RA6 FP | BF+cache FP | New trees |',
            '|---|---|---:|---|---:|---:|---:|---:|---:|']
    losses=[]
    for r in cases_:
        m=r['methods'];z=m['RA6-Z'];old=m['RA6'];bf=m['BF+ReplayCache']
        if z['fp']>old['fp'] or z['fp']>bf['fp']:
            losses.append(r)
            lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {r['workload']} | {r['seed']} | {z['fp']} | {old['fp']} | {bf['fp']} | {z['trees']} |")
    if not losses:lines.append('| — | No failures against either reference in this tested matrix | | | | | | | |')
    diag=diagnostics(cases_)
    lines+=['','## Where the remaining TCP-only losses occur','',
            '| Cache | No zero-tree candidate in top5 | Zero built, learned wins refinement | Zero chosen, different cache fraction from BF replay |',
            '|---|---:|---:|---:|']
    for mode in ('index','fp64'):
        d=diag[mode]['remaining_tcp_losses']
        lines.append(f"| {mode} | {len(d['no_zero_in_shortlist'])} | {len(d['learned_wins_refinement'])} | {len(d['zero_fraction_differs_from_replay'])} |")
    lines+=['', 'This is a stage-location diagnosis, not a proof of causal loss decomposition. Expanded candidate availability does not remove prediction error or future distribution change. Full case details are in diagnostics.json.']
    lines+=['','## Scope and interpretation','',
            '- This is RA6-Z, a new method extension motivated by already observed weak-model failures—not a retroactive rewrite or independent holdout validation of RA6. Frozen methods, parameters and original unfavorable results remain available.',
            '- Zero-tree consumes only the actual BF owning array and chosen cache; model bytes are zero. A standalone reloaded ZeroTreeFilter takes hashes, not features/model arrays, and has a separate authoritative-absence feedback interface. Full native BF/CLOCK tail counts match the frozen simulator for every selected zero-tree result.',
            '- Search still evaluates learned models; choosing zero trees at deployment does not eliminate their training/scoring cost during search. Zero-tree also is not a Direct/no-filter database candidate, and minimizing FP is not minimizing database latency. The round16 negative database result is not resolved by this experiment.',
            '- Merely adding candidates guarantees neither an expanded predictive shortlist containing the old winner nor a future-tail improvement. Zero-Predict diagnoses pure-BF prediction separately; expanded Replay+Z is guaranteed no worse only on its learning replay objective, not on its evaluation tail.',
            '- Exact Replay candidate-build costs are recorded separately and reused per budget; predictive timing includes its own table/top-five builds. Do not quote these unequal-boundary fields as a new selection-speed claim. Models/scores are read from frozen caches, not freshly trained for this effectiveness comparison.',
            '- Indexed negative caches require a member safety index outside the filter budget. The deployed fp64 zero-tree path needs no such index, but collision-related FN limitations remain; the experiment loader still prepares legacy state. Fixed-input member checks are not a guarantee for arbitrary future keys.',
            '- Strong-model controls cover COD/URL/CAIDA/Shalla at one prespecified middle budget each, Zipf1.0 and every-key-once. Fresh-adversarial controls cover all original CAIDA/Shalla budgets. These are not a replacement for the full original1146-case main table.',
            '- The original fresh-adversarial generator is deterministic with respect to seed; its five seed labels do not create five independent traces. Other case sharing also precludes treating192 cases as192 independent trials. No new significance test is asserted.',
            '- Seven synthetic unit checks and two real-cache-format pilot cases precede the formal freeze; the pilot verifies the zero-disabled variant exactly reproduces original RA6. No tuning follows the formal result.']
    columns=list(flat[0])
    columns += sorted({k for row in flat for k in row}-set(columns))
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=columns);writer.writeheader();writer.writerows(flat)
    return {'report.md':'\n'.join(lines)+'\n','rows.csv':buf.getvalue(),'summary.json':json.dumps(stats,indent=2)+'\n','diagnostics.json':json.dumps(diag,indent=2)+'\n'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    allrows,flat,stats,verified=collect(with_inputs=a.inputs)
    for name,text in render(allrows,flat,stats).items():
        target=ROOT/'results'/name
        if a.verify_only:assert target.read_bytes()==text.encode(),name
        else:target.write_bytes(text.encode())
    if not a.verify_only:save(ROOT/'results/verification.json',verified)
    print('PASS:192 cases,1536 method rows, full matrix, native zero-tree checks and all five reference regressions')
