"""Reconstruct the complete first-test tables without model libraries or datasets."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
MODELS=('BF','LR','GaussianNB','Additive16','MLP8','Tree1','Tree16')
SETTINGS={'url':(64,128),'caida_tcp_flow':(16,32)}


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def report(verify=False):
    done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['filter_records']==84
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    assert digest(ROOT/'plan/freeze.json')==done['freeze_sha256']
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h,rel
    rows=[];summary=[]
    lines=['# Lightweight scorers: first static-filter screen','',
           'Two datasets, two budgets each, three fresh deterministic training processes per dataset. '
           'All learned scorers use the same frozen FastPLBF allocator; no negative cache or cache-aware training is included. '
           'Times are native-loop microbenchmarks with amortized Python call overhead, not database or scalar Python API latency.','']
    for ds,budgets in SETTINGS.items():
        runs=[json.loads((ROOT/f'results/main/{ds}_rep{rep}.json').read_text()) for rep in range(3)]
        for rep,r in enumerate(runs):
            assert r['status']=='complete' and r['exit_code']==0 and r['rep']==rep and r['dataset']==ds
            assert r['openblas_threads']==r['numba_threads']==1
            assert len(r['models'])==6 and len(r['filters'])==14
            assert {(x['model'],x['budget_kib']) for x in r['filters']}=={(m,k) for m in MODELS for k in budgets}
            assert r['request_sha256']==runs[0]['request_sha256']
            for x in r['filters']:
                assert x['member_fn']==0 and x['roundtrip_checked'] and x['total_bytes']<=x['budget_kib']*1024
                assert x['total_bytes']==x['model_bytes_with_headers']+x['filter_payload_bytes']+x['metadata_and_headers_bytes']
                assert 0<=x['fp']<=x['negatives']
                t=x['native'];assert len(t['ns_per_query_all'])==3 and all(math.isfinite(v) and v>0 for v in t['ns_per_query_all'])
                assert median(t['ns_per_query_all'])==t['median_ns_per_query']
                rows.append(dict(dataset=ds,rep=rep,model=x['model'],budget_kib=x['budget_kib'],fp=x['fp'],negatives=x['negatives'],
                                 total_bytes=x['total_bytes'],model_bytes=x['model_bytes_with_headers'],
                                 native_query_ns=t['median_ns_per_query'],filter_build_s=x['filter_build_s']))
        lines += [f'## {ds}','', '| Model | Model bytes incl. headers | Train s | AUC | Fit status |','|---|---:|---:|---:|---|']
        for name in MODELS[1:]:
            models=[next(m for m in r['models'] if m['name']==name) for r in runs]
            assert all(m['model_arrays_sha256']==models[0]['model_arrays_sha256'] for m in models)
            status=','.join(sorted({m['fit_status'] for m in models}))
            lines.append(f"| {name} | {models[0]['model_bytes_with_headers']} | {median(m['train_s'] for m in models):.3f} | {models[0]['heldout_auc']:.4f} | {status} |")
        lines+=['','| Model | KiB budget | Negative pool FP | Native model+BF ns/query |','|---|---:|---:|---:|']
        for kib in budgets:
            for name in MODELS:
                group=[x for x in rows if x['dataset']==ds and x['budget_kib']==kib and x['model']==name]
                assert len(group)==3 and len({x['fp'] for x in group})==1
                t=median(x['native_query_ns'] for x in group);f=group[0]['fp']
                lines.append(f'| {name} | {kib} | {f:,} | {t:.1f} |')
                summary.append(dict(dataset=ds,budget_kib=kib,model=name,fp=f,model_bytes=group[0]['model_bytes'],native_query_ns=t))
    lines+=['','## Boundaries','',
            '- URL Additive16/MLP8 reached the fixed optimization limit without convergence; they are not best-tuned representatives. The records retain status and objective; no retries/hyperparameter changes followed the outcomes.',
            '- GaussianNB has different model assumptions and training loss. Tree1/16 are fixed controls, not the original200-prefix search. All three training runs use the same seed/data and are timing repeats, not statistical generalization trials.',
            '- Model bytes include required standardization/bin edges and owning-array headers; common request features/prehashed keys and interpreter/JIT state are excluded. PureBF uses its strongest one-array representation. Filter metadata is not hidden.',
            '- Native model+BF loop includes per-request feature normalization/binning/tree traversal and BF probes. It excludes raw URL extraction and hash calculation for all methods. No precomputed scores/flags substitute timed queries. Percentile scalar API latency is not measured.',
            '- Smaller models can trade additional FP for lower memory and inference cost; these data do not establish database speedup or a universally superior model. TCP-only uses the same stored address encoding, whose lack of information is not fixed by changing classifiers.',
            '- This new experiment branch does not modify frozen RA6, cache prediction, prior papers, published historical results or the existing dependency environment. Direct partition tables and cost-weighted training are separate follow-on hypotheses.']
    out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    products={'report.md':'\n'.join(lines)+'\n','rows.csv':out.getvalue(),'summary.json':json.dumps(summary,indent=2)+'\n'}
    for name,text in products.items():
        p=ROOT/'results'/name
        if verify:assert p.read_bytes()==text.encode()
        else:p.write_bytes(text.encode())
    print('PASS:36 trained scorer records,84 complete physical-budget filter records; deterministic/native checks')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');report(p.parse_args().verify_only)
