"""Post-run arithmetic/encoding audit, separate from the frozen experiment driver.
Requires local prepared input; does not run methods, change outcomes, or retime selection.
"""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import sys,time,json,hashlib,csv
from pathlib import Path
import numpy as np
import pandas as pd
HERE=Path(__file__).resolve().parent;BLOOM=HERE.parents[1]
WR=BLOOM/'windows_research';ROOT=WR/'round53_index_free_recheck_v4';CACHE=WR/'round2_backlog/cache'
BUDGETS={'url':(64,128,256),'caida_flow':(16,24,32,256),'mawi2020_flow':(16,24,32,128),'mawi2021_flow':(16,24,32,128),'mawi2022_flow':(16,24,32,128),'mawi2024_flow':(16,24,32,128),'cod':(256,1024,4096),'caida':(128,256,1024,2048),'shalla':(256,1024,2048,4096)}
METHODS=('Gama','Gama+10%','Replay','RA-global','RA-PLBF-GT19','BF+Exact','PlainBF')


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def load(p):return json.loads(p.read_text())


def audit():
    start=time.perf_counter();assert load(ROOT/'results/completion.json')['status']=='complete'
    checked={}
    for round_name in ('round53_index_free_recheck','round53_index_free_recheck_v2','round53_index_free_recheck_v3','round53_index_free_recheck_v4'):
        freeze=load(WR/round_name/'plan/freeze.json')
        for group in ('sources','inputs'):
            for p,h in freeze[group].items():
                if p not in checked:checked[p]=sha(BLOOM/p)
                assert checked[p]==h,p
    assert load(WR/'round53_index_free_recheck/results/failure.json')['status']=='failed'
    assert not (WR/'round53_index_free_recheck/results/completion.json').exists()
    for name in ('round53_index_free_recheck_v2','round53_index_free_recheck_v3'):
        assert load(WR/name/'results/failure.json')['error_type']=='MemoryError'
        assert not (WR/name/'results/completion.json').exists()
    provenance=load(ROOT/'results/reuse_provenance.json')
    assert provenance['reused_cases']==38 and provenance['reused_rows']==266
    for item in provenance['files']:
        assert sha(ROOT/item['path'])==sha(BLOOM/item['source'])==item['sha256']
    def strip_timing(x):
        if isinstance(x,dict):return {k:strip_timing(v) for k,v in x.items() if not k.endswith(('_s','_seconds')) and k not in ('peak_rss_bytes','pilot')}
        if isinstance(x,list):return [strip_timing(v) for v in x]
        return x
    for ds,k in (('url',64),('caida_flow',16)):
        assert strip_timing(load(ROOT/f'results/pilot_{ds}_{k}.json'))==strip_timing(load(ROOT/f'results/{ds}_{k}.json'))
    assert load(ROOT/'results/workspace_equivalence.json')['status']=='passed'
    encodings=[]
    for ds in BUDGETS:
        t=time.perf_counter();meta=load(ROOT/f'results/raw_{ds}.json')
        assert sha(ROOT/f'cache/{ds}.npz')==meta['prepared_sha256']
        with np.load(CACHE/ds/'data.npz',allow_pickle=False) as f:ids,y=f['ids'],f['y']
        with np.load(ROOT/f'cache/{ds}.npz',allow_pickle=False) as f:blob,off=f['blob'],f['offsets']
        assert len(off)==len(ids)+1 and off[0]==0 and off[-1]==len(blob)
        assert meta['keys']==len(ids) and meta['members']==int(y.sum())
        if ds in ('cod','caida'):
            assert np.all(np.diff(off)==8) and np.array_equal(blob.view('<u8'),ids)
        else:
            for a in range(0,len(ids),100000):
                b=min(a+100000,len(ids));text=[]
                if ds.endswith('_flow'):
                    w=33 if ds=='caida_flow' else 9;nb=(w-1)//2
                    assert np.all(np.diff(off[a:b+1])==w)
                    for i in range(a,b):
                        k=memoryview(blob)[int(off[i]):int(off[i+1])]
                        src=int.from_bytes(k[:nb],'little');dst=int.from_bytes(k[nb:2*nb],'little');lab=int(k[-1])
                        assert lab in (0,1) and bool(lab)==bool(y[i])
                        text.append(f'{src}>{dst}#{lab}')
                else:
                    text=[blob[off[i]:off[i+1]].tobytes().decode('utf-8') for i in range(a,b)]
                hid=pd.util.hash_pandas_object(pd.Series(text),index=False).to_numpy(np.uint64)
                assert np.array_equal(hid,ids[a:b]),f'Full decoded raw key identity mismatch: {ds}'
        encodings.append(dict(dataset=ds,keys=len(ids),decoded_identity_pass=True,width=meta['schema_width'],wall_s=time.perf_counter()-t))
        del ids,y,blob,off
    rows=[]
    for ds,ks in BUDGETS.items():
        invariant_streams={}
        for k in ks:
            run=load(ROOT/f'results/{ds}_{k}.json');assert run['status']=='complete' and run['member_index_built'] is False
            assert run['peak_rss_bytes']<6*1024**3
            assert run['cache_schema_width']==(33 if ds=='caida_flow' else 9 if ds.endswith('_flow') else 8 if ds in ('cod','caida') else 128)
            for w in run['workloads']:
                sig=(w['stream_sha256'],w['learning_sha256'],w['tail_sha256'],w['learning_queries'],w['tail_queries'])
                if w['workload'] in invariant_streams:assert invariant_streams[w['workload']]==sig
                invariant_streams[w['workload']]=sig
            rows+=run['rows']
    expected={(ds,k,w,0,m) for ds,ks in BUDGETS.items() for k in ks for w in (('真实轨迹',) if ds.endswith('_flow') else ('每key一次','uniform-全部','zipf1.0-全部')) for m in METHODS}
    key=lambda r:(r['dataset'],r['budget_kib'],r['workload'],r['seed'],r['method'])
    by={key(r):r for r in rows};assert len(by)==len(rows)==434 and set(by)==expected
    for r in rows:
        assert r['required_member_index_bytes']==r['member_BF_FN']==r['final_member_cache_hits']==0
        assert r['total_bytes']==sum(r[k] for k in ('model_bytes','bf_bytes','metadata_bytes','header_bytes','cache_bytes'))<=r['budget_kib']*1024
        assert r['cache_slots']%4==0
        if r['cache_bytes']:
            w=33 if r['dataset']=='caida_flow' else 9 if r['dataset'].endswith('_flow') else 8 if r['dataset'] in ('cod','caida') else 128
            assert r['cache_bytes']==112+32+(r['cache_slots']//4)*(4*(w+4)+1)
        if r['method']=='Gama':assert r['Gama_old_FP_regression'] is True and r['cache_bytes']==0
    report=load(ROOT/'results/verification.json');summary={}
    for method in METHODS:
        if method=='RA-PLBF-GT19':continue
        pairs=[(r,by[(*key(r)[:-1],method)]) for r in rows if r['method']=='RA-PLBF-GT19']
        ratios=[(a['fp']+1)/(b['fp']+1) for a,b in pairs]
        s=dict(cases=62,wins=sum(a['fp']<b['fp'] for a,b in pairs),ties=sum(a['fp']==b['fp'] for a,b in pairs),losses=sum(a['fp']>b['fp'] for a,b in pairs),median_paired_smoothed_FP_ratio=float(np.median(ratios)),RA_FP_sum=sum(a['fp'] for a,b in pairs),baseline_FP_sum=sum(b['fp'] for a,b in pairs))
        for k,v in s.items():assert report['summary']['all'][method][k]==v
        summary[method]=s
    with (ROOT/'results/main.csv').open() as f:
        table=list(csv.DictReader(f));assert len(table)==434
        for r in table:
            k=(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['method'])
            for field in ('fp','total_bytes','cache_bytes','member_BF_FN','final_member_cache_hits'):assert int(r[field])==by[k][field]
    result=dict(status='passed',source_input_files_checked=len(checked),original_failure_preserved=True,both_memory_stops_preserved=True,reused_cases=38,new_cases=24,workspace_equivalence_cases=4,decoded_raw_key_identity=encodings,cases=62,rows=434,all_zero_FN_and_budget_checks=True,all_deployment_member_indices_zero=True,budget_invariant_streams=True,summary=summary,wall_s=time.perf_counter()-start,note='Project-local independent arithmetic/encoding audit, not third-party or independent holdout; not a new timing run.')
    (HERE/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':audit()
