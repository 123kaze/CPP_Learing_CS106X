"""Verify training guarantees separately from future-tail outcomes; stdlib only."""
import argparse
import csv
import io
import json
from statistics import median
from common20 import ROOT,WR,BLOOM,DATASETS,METHODS,cases,digest,save


def compare(rows,ref):
    a=[r['methods']['RA6-ZGate']['fp'] for r in rows]
    b=[r['methods'][ref]['fp'] for r in rows]
    return dict(cases=len(rows),wins=sum(x<y for x,y in zip(a,b)),ties=sum(x==y for x,y in zip(a,b)),
                losses=sum(x>y for x,y in zip(a,b)),median_ratio=median((x+1)/(y+1) for x,y in zip(a,b)),
                worst_ratio=max((x+1)/(y+1) for x,y in zip(a,b)),
                zero_selected=sum(r['gate']['family']=='zero' for r in rows))


def collect(root=ROOT,with_inputs=False):
    assert __debug__,'Assertions required'
    bloom=root.parents[1];wr=root.parent;files={}
    def load(p):
        files[str(p.relative_to(bloom))]=digest(p)
        return json.loads(p.read_text())
    manifest=load(root/'results/manifest.json');freeze=load(root/'plan/freeze.json')
    assert manifest['freeze']==freeze and manifest['methods']==list(METHODS)
    assert manifest['cases']==json.loads(json.dumps({ds:cases(ds) for ds in DATASETS}))
    for rel,h in freeze['sources'].items():assert digest(bloom/rel)==h,rel
    if with_inputs:
        for rel,h in freeze['inputs'].items():assert digest(bloom/rel)==h,rel
    done=load(root/'results/completion.json')
    assert done==dict(status='complete',jobs=16,cases=192,live_method_rows=576,learning_nonregression_cases=192,
                     manifest_sha256=digest(root/'results/manifest.json'))
    expected={f'{ds}_{mode}' for ds in DATASETS for mode in ('index','fp64')}
    for ext in ('.json','.log'):
        assert {p.stem for p in (root/'results/main').glob('*'+ext)}==expected
    allrows=[];flat=[]
    for ds in DATASETS:
        for mode in ('index','fp64'):
            p=root/f'results/main/{ds}_{mode}.json';r=load(p)
            assert r['status']=='ok' and r['exit_code']==0 and not r['pilot']
            assert (r['dataset'],r['cache'])==(ds,mode)
            assert len(r['cases'])==len(cases(ds))
            assert {(x['budget_kib'],x['workload'],x['seed'],x['cohort']) for x in r['cases']}==set(cases(ds))
            log=p.with_suffix('.log');text=log.read_text()
            assert 'Traceback' not in text and f'COMPLETE {ds} {mode}:' in text
            files[str(log.relative_to(bloom))]=digest(log)
            reference=wr/f'round17_zerotree/results/main/{ds}_{mode}.json'
            ref=load(reference)
            assert r['round17_archive_sha256']==digest(reference)==freeze['inputs'][str(reference.relative_to(bloom))]
            prior={(c['budget_kib'],c['workload'],c['seed']):c for c in ref['results']}
            for c in r['cases']:
                old=prior[c['budget_kib'],c['workload'],c['seed']]
                assert (c['base_stream_sha256'],c['tail_stream_sha256'],c['tail_len'])==(old['base_stream_sha256'],old['tail_stream_sha256'],old['tail_len'])
                g=c['gate'];assert g['empirical_nonregression']
                assert g['selected_learning_fp']==min(g['zero_learning_fp'],g['anchor_learning_fp'])
                assert (g['family']=='zero')==(g['zero_learning_fp']<=g['anchor_learning_fp'])
                assert g['zero_learning_fp']==old['bf_replay_learn_fp']
                assert g['zero_candidates']==13 and g['learned_finalists']==1
                assert len(g['replay_records'])==13
                assert g['zero_processed_queries']==sum(x['processed'] for x in g['replay_records'])<=12*c['learn_len']
                assert all(0<=x['processed']<=c['learn_len'] for x in g['replay_records'])
                assert set(c['methods'])==set(METHODS)
                selected=c['methods']['BF+ReplayCache' if g['family']=='zero' else 'RA6-GT19']
                assert c['methods']['RA6-ZGate']==selected
                assert c['historical_predictive_zero']==old['methods']['RA6-Z']
                assert c['historical_full_replay']==old['methods']['Replay+Z']
                for method,m in c['methods'].items():
                    assert type(m['fp']) is int and 0<=m['fp']<=c['tail_len']
                    assert m['member_checks_passed'] and m['cache_bytes']<=m['total_bytes']<=c['budget_kib']*1024
                    if m['trees']==0:assert m['native_zero_checks'] and m['model_bytes']==0
                    if method!='RA6-ZGate':
                        archived=old['methods']['RA6' if method=='RA6-GT19' else method]
                        for k in ('trees','frac','cache_bytes','total_bytes','model_bytes','fp','hits','static_flags_sha256'):
                            assert m[k]==archived[k],(ds,method,k)
                    flat.append(dict(dataset=ds,cache=mode,budget_kib=c['budget_kib'],workload=c['workload'],seed=c['seed'],cohort=c['cohort'],
                                     method=method,tail_len=c['tail_len'],trees=m['trees'],frac=m['frac'],cache_bytes=m['cache_bytes'],
                                     total_bytes=m['total_bytes'],fp=m['fp'],hits=m['hits']))
                allrows.append(c)
    assert len(allrows)==192 and len(flat)==576
    for mode in ('index','fp64'):
        pilot=load(root/f'results/pilot/caida_tcp_flow_{mode}.json')
        assert pilot['status']=='ok' and pilot['exit_code']==0 and pilot['pilot_exhaustive_learning_check']
    summary={}
    for mode in ('index','fp64'):
        for cohort in ('weak_tcp','model_control','fresh_adversarial'):
            rr=[r for r in allrows if r['cache']==mode and r['cohort']==cohort]
            assert len(rr)==(16 if cohort=='weak_tcp' else 40)
            summary[f'{mode}/{cohort}']={ref:compare(rr,ref) for ref in ('BF+ReplayCache','RA6-GT19')}
    return allrows,flat,summary,dict(status='verified',cases=192,learning_guarantee_cases=192,live_method_rows=576,
                                    checked_raw_inputs=with_inputs,records=files)


def render(rows,flat,summary):
    lines=['# RA6-ZGate: explicit no-model protection through learning replay','',
           '192 cases;13 BF/cache configurations plus one repaired RA6 finalist. The choice uses only exact learning FP; ties select the no-model winner. All192 learning inequalities were checked. Future-tail outcomes below are not used to select candidates.','',
           '| Cache | Cohort | Reference | Cases | Zero selected | Tail FP ratio median | Win/tie/loss | Worst ratio |',
           '|---|---|---|---:|---:|---:|---|---:|']
    for key,v in summary.items():
        mode,cohort=key.split('/')
        for ref,s in v.items():
            lines.append(f"| {mode} | {cohort} | {ref} | {s['cases']} | {s['zero_selected']} | {s['median_ratio']:.6f} | {s['wins']}/{s['ties']}/{s['losses']} | {s['worst_ratio']:.6f} |")
    lines+=['','## TCP-only: training and future counted separately','',
            '| Cache | Dataset | KiB | Family | Learn BF | Learn RA6 | Learn chosen | Tail BF | Tail RA6 | Tail chosen |',
            '|---|---|---:|---|---:|---:|---:|---:|---:|---:|']
    for r in rows:
        if r['cohort']!='weak_tcp':continue
        g=r['gate'];m=r['methods']
        lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {g['family']} | {g['zero_learning_fp']} | {g['anchor_learning_fp']} | {g['selected_learning_fp']} | {m['BF+ReplayCache']['fp']} | {m['RA6-GT19']['fp']} | {m['RA6-ZGate']['fp']} |")
    lines+=['','## All future-tail regressions against either reference','',
            '| Cache | Dataset | KiB | Workload | Seed | Family | Chosen FP | BF FP | RA6 FP |',
            '|---|---|---:|---|---:|---|---:|---:|---:|']
    for r in rows:
        m=r['methods'];f=m['RA6-ZGate']['fp'];b=m['BF+ReplayCache']['fp'];a=m['RA6-GT19']['fp']
        if f>b or f>a:lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {r['workload']} | {r['seed']} | {r['gate']['family']} | {f} | {b} | {a} |")
    lines+=['','## Interpretation and boundaries','',
            '- This is a new selector, not the old predictive RA6-Z. BF candidates cannot be excluded by predicted top-five pruning. The guaranteed objective is min(learning FP of BF-replay winner, learning FP of repaired RA6), not min of unknowable future FP.',
            '- Exact learning replay is paid for:13 BF candidates plus one learned-anchor replay, with original early stopping/no-cache shortcuts. Per-case timers include builds and replay, but this is not a new controlled timing/scalability campaign; model/scores are loaded and first-use JIT may contribute. No transfer of the old49.24× statistic-only speedup claim.',
            '- Repaired RA6 and BF controls reproduce archived round17 configurations, full static flags, tail FP/hits, and BF training objectives. Their repaired statistic arrays are checked equal to the original on this fixed matrix. Historical predictive RA6-Z/expandedReplay values are retained only as explicitly labeled historical comparators.',
            '- Each chosen candidate is actually evaluated after selection, and selected zero-tree paths receive full-tail native BF/CLOCK and populated-cache member checks. No model or features are required for zero-tree deployment; search still evaluates a learned model.',
            '- FP ratios use+1 smoothing per case before medians. Same workloads/models recur; five fresh-adversarial seed labels can describe the same deterministic stream. No independent-sample significance claim, oracle gate or parameter retuning.',
            '- External index cost and fp64 collision limitations remain. This does not provide a Direct/no-filter database candidate or prove latency improvement. Paper and prior frozen sources are unchanged.',
            '- In the inspected original G-PLBF adaptive script, best_epoch=0 is initialization and the search lower bound is2; shared Gama prefixes start at1. No genuine zero-tree BF fallback exists in those inspected paths. This is not a statement about all possible Gama variants.']
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    return {'report.md':'\n'.join(lines)+'\n','rows.csv':b.getvalue(),'summary.json':json.dumps(summary,indent=2)+'\n'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    rows,flat,summary,verified=collect(with_inputs=a.inputs)
    for name,text in render(rows,flat,summary).items():
        p=ROOT/'results'/name
        if a.verify_only:assert p.read_bytes()==text.encode(),name
        else:p.write_bytes(text.encode())
    if not a.verify_only:save(ROOT/'results/verification.json',verified)
    print('PASS:192 full cases, learning non-regression checked independently of future-tail outcomes')
