"""Separate read-only TCP-only supplement, not part of the original1146 main cases."""
from audit18 import *


def main():
    out=ROOT/'results/tcp_supplement.json';assert not out.exists()
    meta_path=WR/'round11_tcp/results/datasets.json'
    registry=json.loads(meta_path.read_text())
    refpath=WR/'round13_complete/results/combined_baseline_rows.csv'
    with refpath.open() as f:refs=[r for r in csv.DictReader(f) if r['cache']=='index' and r['cohort']=='tcp']
    assert len(refs)==16
    streams=[];rows=[];hashes={str(meta_path.relative_to(BLOOM)):digest(meta_path),str(refpath.relative_to(BLOOM)):digest(refpath)}
    for ds in registry:
        setup,safe,inputs=B.load_setup(ds,'fp64');assert safe is None
        for p in inputs:hashes[str(p.relative_to(BLOOM))]=digest(p)
        with np.load(B.C.CACHE/ds/'data.npz') as raw:assert not raw['y'][setup.split['neg_test']].any()
        base=B.C.load_flow_trace(setup);n=len(base)//4;h=ah(base)
        matching=[r for r in refs if r['dataset']==ds]
        assert len(matching)==4 and all(r['base_stream_sha256']==h and int(r['tail_len'])==len(base)-n for r in matching)
        result=examine(base[:n])
        stream=dict(dataset=ds,cohort='tcp_supplement',workload='真实轨迹',seed=0,base_len=len(base),pool_keys=len(setup.h1q),
                    base_stream_sha256=h,learning_stream_sha256=ah(base[:n]),budgets=registry[ds]['budgets_kib'],**result)
        streams.append(stream)
        rows += [dict(stream,budget_kib=int(r['budget_kib'])) for r in matching]
        print(f'TCP AUDIT {ds}: gaps={result["gap_c"]} affected={result["gap_learning_queries"]}/{n} total mass={result["original_total_mass"]:.10f}',flush=True)
    for rel,h in hashes.items():assert digest(BLOOM/rel)==h
    save(out,dict(status='complete',cohort='tcp_supplement',streams=streams,cases=rows,inputs=hashes,
                  note='16 supplementary TCP-only settings; not included in the original1146/holdout1150 count'))


if __name__=='__main__':main()
