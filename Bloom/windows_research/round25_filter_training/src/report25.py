"""Offline reconstruction of matched-capacity training-objective results."""
import argparse
import csv
import io
import json
import hashlib
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
SETTINGS={'url':(64,128),'caida_tcp_flow':(16,32)}
METHODS=('BCE100','BCE200','FilterAware','BF')


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def collect():
    done=json.loads((ROOT/'results/completion.json').read_text());freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    assert done['status']=='complete' and done['filter_records']==48 and done['jobs']==6
    assert done['freeze_sha256']==digest(ROOT/'plan/freeze.json')
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h,rel
    rows=[]
    for ds,kk in SETTINGS.items():
        for seed in (1,2,3):
            p=ROOT/f'results/main/{ds}_seed{seed}.json';r=json.loads(p.read_text())
            assert r['status']=='complete' and r['exit_code']==0 and r['dataset']==ds and r['seed']==seed
            assert r['openblas_threads']==r['numba_threads']==1
            assert len(r['records'])==8
            assert {(x['budget_kib'],x['method']) for x in r['records']}=={(k,m) for k in kk for m in METHODS}
            baseline=json.loads((ROOT.parent/f'round23_lightweight/results/main/{ds}_rep0.json').read_text())
            assert r['request_sha256']==baseline['request_sha256']
            for k in kk:
                by={x['method']:x for x in r['records'] if x['budget_kib']==k}
                learned=[by[m] for m in METHODS[:-1]]
                assert len({x['model_payload_bytes'] for x in learned})==1
                assert len({x['model_bytes_with_headers'] for x in learned})==1
                assert by['BF']['fp']==next(x['fp'] for x in baseline['filters'] if x['model']=='BF' and x['budget_kib']==k)
                if seed==1:
                    old=next(x for x in baseline['filters'] if x['model']=='MLP8' and x['budget_kib']==k)
                    assert by['BCE100']['fp']==old['fp'] and by['BCE100']['flags_sha256']==old['static_flags_sha256']
                for x in learned:
                    assert x['member_fn']==0 and x['native_flags_exact'] and x['reload_exact']
                    assert x['total_bytes']<=k*1024
                    assert x['total_bytes']==x['model_bytes_with_headers']+x['filter_payload_bytes']+x['metadata_and_headers_bytes']
                    assert x['fp']>=0 and x['fp']<=x['negatives']
                    for name in ('score_ns','query_ns'):
                        assert len(x[name+'_all'])==3 and all(math.isfinite(v) and v>0 for v in x[name+'_all'])
                        assert median(x[name+'_all'])==x[name+'_median']
                    assert 0<x['soft_training_J']<=1 and 0<x['hard_training_J']<=1
                    assert x['training_s_charged']==r['warm_train_s']+(x['optimizer']['seconds'] if x['optimizer'] else 0)
                    if x['optimizer'] is not None:
                        assert x['optimizer']['iterations']<=100
                        assert math.isfinite(x['optimizer']['objective'])
                rows+= [dict(dataset=ds,**x) for x in by.values()]
    assert len(rows)==48
    return rows


def render(rows):
    lines=['# Same MLP8: static filter-aware training versus classification training','',
           'Same model parameter count, original features, training split and native scoring/filter implementation. '
           'Three different initialization seeds, each shared between branches. Common BCE warm start of up to100 iterations; '
           'BCE200 and FilterAware each receive up to100 further iterations. Different function-evaluation/wall costs are reported, not assumed equal. '
           'No negative cache, quantization or global joint optimality claim.', '',
           '| Dataset | KiB | Method | Test FP (seeds1/2/3) | Median FP | Model bytes incl. headers | Native query ns | Charged training s | Continuation converged |',
           '|---|---:|---|---|---:|---:|---:|---:|---|']
    stats=[]
    for ds,kk in SETTINGS.items():
        for k in kk:
            by={m:sorted([x for x in rows if x['dataset']==ds and x['budget_kib']==k and x['method']==m],key=lambda r:r['seed']) for m in METHODS}
            for m,rr in by.items():
                fps='/'.join(str(x['fp']) for x in rr)
                if m=='BF':lines.append(f'| {ds} | {k} | BF | {fps} | {median(x["fp"] for x in rr)} | 0 | not timed here | not timed here | n/a |');continue
                converged='warm baseline' if m=='BCE100' else f"{sum(x['optimizer']['success'] for x in rr)}/3"
                lines.append(f"| {ds} | {k} | {m} | {fps} | {median(x['fp'] for x in rr)} | {rr[0]['model_bytes_with_headers']} | {median(x['query_ns_median'] for x in rr):.1f} | {median(x['training_s_charged'] for x in rr):.3f} | {converged} |")
            a,b=by['FilterAware'],by['BCE200']
            stats.append(dict(dataset=ds,budget_kib=k,comparison='FilterAware/BCE200',
                fp_ratios=[(x['fp']+1)/(y['fp']+1) for x,y in zip(a,b)],
                wins=sum(x['fp']<y['fp'] for x,y in zip(a,b)),ties=sum(x['fp']==y['fp'] for x,y in zip(a,b)),
                losses=sum(x['fp']>y['fp'] for x,y in zip(a,b)),
                query_time_ratios=[x['query_ns_median']/y['query_ns_median'] for x,y in zip(a,b)]))
    lines+=['','## Soft objective versus actual deployment','',
            '| Dataset | KiB | Method | Median soft training J | Median hardened training J | Median actual test FPR |',
            '|---|---:|---|---:|---:|---:|']
    for ds,kk in SETTINGS.items():
        for k in kk:
            for m in METHODS[:-1]:
                rr=[x for x in rows if x['dataset']==ds and x['budget_kib']==k and x['method']==m]
                lines.append(f"| {ds} | {k} | {m} | {median(x['soft_training_J'] for x in rr):.8f} | {median(x['hard_training_J'] for x in rr):.8f} | {median(x['fp']/x['negatives'] for x in rr):.8f} |")
    lines+=['','## Interpretation','',
            '- URL128KiB is the positive local result:all3 FilterAware initializations lower actual FP than continued BCE at identical model size. URL64KiB improves only1 of3. Neither budget establishes a universal advantage or significance with three model seeds.',
            '- TCP-only learned branches remain worse than plainBF. All scores can be nearly uninformative on the current address encoding; changing the training objective does not guarantee new information.',
            '- URL continuation optimizers hit the prespecified100-iteration limit in both branches. These are fixed-compute-budget trials, not converged globally optimal models. Retain function evaluations, gradient norms and wall times; do not claim equal time from equal iteration ceilings.',
            '- A lower soft proxy does not imply proportionally lower deployed FP. Training uses smoothed soft-region class histograms and an estimated capped continuous BF objective; deployment uses hard scores, validation-driven FastPLBF partitions and integer BF probing. The hard-training diagnostic fixes the soft training cuts, so it is not identical to final deployment routing either.',
            '- Mean/std and soft-cut/temperature calibration use only training observations. Both branches start from exactly the same warm weights. Test/negative-validation values do not select model checkpoints, losses or hyperparameters. All models are evaluated even when worse.',
            '- Model bytes, normalization and navigation/array overhead are charged before BF bits. All members are inserted and verified in final regions. Native scoring matches reference arithmetic, every key matches frozen BF flags, and reloaded arrays reproduce all query decisions.',
            '- Native timing uses fixed100K requests in a compiled loop with batch-amortized call overhead. Standardization is included; raw feature extraction, key hashing, Python scalar API overhead and database access are not. No p99 or end-to-end throughput result is asserted.',
            '- No cache-aware residual weights, direct multi-output router, quantization, KL threshold or zero-tree selection algorithm is part of this experiment. These are separate possible next steps, not completed claims. Existing RA6/paper files and old frozen experiments remain unchanged.']
    flat=[]
    for x in rows:
        if x['method']=='BF':continue
        flat.append({k:x[k] for k in ('dataset','budget_kib','seed','method','fp','negatives','total_bytes','model_bytes_with_headers',
            'soft_training_J','hard_training_J','score_ns_median','query_ns_median','training_s_charged','filter_build_s','heldout_auc')})
    b=io.StringIO(newline='');w=csv.DictWriter(b,fieldnames=list(flat[0]));w.writeheader();w.writerows(flat)
    return {'report.md':'\n'.join(lines)+'\n','comparisons.json':json.dumps(stats,indent=2)+'\n','rows.csv':b.getvalue()}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    for name,text in render(collect()).items():
        out=ROOT/'results'/name
        if a.verify_only:assert out.read_bytes()==text.encode(),name
        else:out.write_bytes(text.encode())
    print('PASS:48 complete records, identical capacity, original warm baseline reproduced, actual FP/native checks')
