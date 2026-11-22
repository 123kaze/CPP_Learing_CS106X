import sys,json,csv,hashlib,time
from pathlib import Path
import numpy as np
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=BLOOM/'windows_research'

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def storage(a):
    assert isinstance(a,np.ndarray)
    seen=set();chain=[];x=a
    while x is not None and id(x) not in seen:
        assert isinstance(x,(np.ndarray,bytes,bytearray)),type(x)
        seen.add(id(x));chain.append(dict(type=type(x).__name__,shallow_bytes=sys.getsizeof(x),logical_bytes=x.nbytes if isinstance(x,np.ndarray) else len(x),owning=bool(x.flags.owndata) if isinstance(x,np.ndarray) else True))
        x=x.base if isinstance(x,np.ndarray) else None
    return dict(shape=list(a.shape),dtype=str(a.dtype),logical_payload_bytes=a.nbytes,view_shallow_bytes=sys.getsizeof(a),retained_chain_bytes=sum(r['shallow_bytes'] for r in chain),chain=chain)

def save(p,data):
    with p.open('x') as f:json.dump(data,f,indent=2);f.write('\n')

def main():
    started=time.perf_counter();freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for sec in ('sources','inputs'):
        for p,h in freeze[sec].items():assert sha(BLOOM/p)==h,p
    with np.load(WR/'round36_http_qualification/cache/clarknet.npz',allow_pickle=False) as d:measure=storage(d['X'])
    assert measure['logical_payload_bytes']==3153200 and measure['view_shallow_bytes']==128 and measure['retained_chain_bytes']==3153440
    ledger=[]
    for seed in (3601,3602,3603):
        old=json.loads((WR/f'round42_raw_key_sqlite/results/seed{seed}.json').read_text());assert old['status']=='complete' and old['preparation']['feature_matrix_bytes']==128
        ledger.append(dict(seed=seed,old_misnamed_feature_matrix_bytes=128,**measure))
    with (WR/'round42_raw_key_sqlite/results/resources_and_latency.csv').open() as f:rows=list(csv.DictReader(f))
    assert len(rows)==63
    corrected=[]
    for r in rows:
        corrected.append(dict(**r,input_feature_payload_bytes=measure['logical_payload_bytes'],input_feature_retained_chain_bytes=measure['retained_chain_bytes'],query_timing_provenance='unchanged_round42_archive'))
    with (ROOT/'results/resources_and_latency_corrected.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(corrected[0]),lineterminator='\n');w.writeheader();w.writerows(corrected)
    with (ROOT/'results/resources_and_latency_corrected.csv').open() as f:back=list(csv.DictReader(f))
    for old,new in zip(rows,back):assert all(new[k]==v for k,v in old.items())
    save(ROOT/'results/feature_storage.json',ledger)
    for sec in ('sources','inputs'):
        for p,h in freeze[sec].items():assert sha(BLOOM/p)==h,p
    save(ROOT/'results/verification.json',dict(status='verified',cases=63,seeds=3,old_columns_unchanged=True,sql_timings_rerun=False,FP_changed=False,filter_budget_changed=False,feature_matrix=measure,seconds=time.perf_counter()-started))
    print(json.dumps(measure,indent=2));print('All63 resource rows retain original timing/FP/Filter fields; old files unchanged.')

if __name__=='__main__':main()
