"""Verify the installed repair on actual main and supplementary learning streams."""
from entry19 import *
import argparse
import numpy as np
from summarize19 import summarize19
sys.path.insert(0,str(WR/'round18_gt_audit/src'))
import audit18 as A
B=A.B;E5=A.E5


def compare(learn,label,old_rate_hash=None):
    old=ORIGINAL_SUMMARIZE(learn,True)
    with patched():new=ra4.summarize(learn,True)
    for key in ('keys','counts'):assert getattr(old,key).tobytes()==getattr(new,key).tobytes()
    for key in ('L','N1','state_bytes'):assert getattr(old,key)==getattr(new,key)
    nc=np.bincount(old.counts)
    gaps=[c for c in range(2,6) if c<len(nc) and nc[c] and (c+1>=len(nc) or nc[c+1]==0)]
    mask=np.isin(old.counts,gaps)
    assert np.all(new.rate>=old.rate)
    assert old.rate[~mask].tobytes()==new.rate[~mask].tobytes()
    assert np.array_equal(new.rate[mask],old.counts[mask]/old.L)
    if old_rate_hash:assert ah(old.rate)==old_rate_hash
    return dict(label=label,L=old.L,distinct_keys=len(old.keys),repair_bins=gaps,changed_keys=int(mask.sum()),
                rate_bit_equal=old.rate.tobytes()==new.rate.tobytes(),original_rate_sha256=ah(old.rate),
                repaired_rate_sha256=ah(new.rate),learning_sha256=ah(learn),N1=old.N1,
                original_total_mass=float(old.rate.sum()+old.N1/old.L),repaired_total_mass=float(new.rate.sum()+new.N1/new.L))


def setup(ds):
    s,_,paths=B.load_setup(ds,'fp64')
    return s,np.argsort(s.q_score,kind='stable'),paths


def stream(s,order,name,spec,seed=0,queries=10_000_000):
    if spec is None:return B.C.load_flow_trace(s)
    import exp2_repetition_cache as E2
    E2.QUERIES=queries
    return E5.R.make_stream(spec,len(s.h1q),np.random.default_rng(2000+seed),order)


def main_dataset(ds):
    output=ROOT/f'results/audit_{ds}.json';assert not output.exists()
    reference=json.loads((WR/f'round18_gt_audit/results/{ds}.json').read_text())
    s,order,paths=setup(ds)
    specs=dict(E5.workload_specs(len(s.h1q))) if not ds.endswith('_flow') else {'真实轨迹':None}
    out=[]
    for r in reference['streams']:
        base=stream(s,order,r['workload'],specs[r['workload']],r['seed'])
        assert ah(base)==r['base_stream_sha256']
        test=compare(base[:len(base)//4],f"{ds}/{r['workload']}/seed{r['seed']}",r['original_rate_sha256'])
        assert test['L']==r['L']
        test.update(dataset=ds,workload=r['workload'],seed=r['seed'],budgets=r['budgets'],cohort=r['cohort'])
        out.append(test)
    save(output,dict(status='complete',dataset=ds,streams=out,inputs={str(p.relative_to(BLOOM)):digest(p) for p in paths},
                     original_audit_sha256=digest(WR/f'round18_gt_audit/results/{ds}.json')))
    print(f'AUDITED {ds}: {len(out)} streams, changed {sum(not r["rate_bit_equal"] for r in out)}',flush=True)


def extras():
    output=ROOT/'results/audit_extras.json';assert not output.exists()
    rows=[];inputs={}
    # Sensitivity learning shares; other E10 knobs use the same25% learning input.
    settings=(('caida_flow','真实轨迹'),('caida','zipf1.0-全部'),('cod','zipf1.0-10万'),('url','全新对抗'))
    for ds,name in settings:
        s,order,paths=setup(ds);inputs.update({str(p.relative_to(BLOOM)):digest(p) for p in paths})
        spec=None if ds.endswith('_flow') else dict(E5.workload_specs(len(s.h1q)))[name]
        base=stream(s,order,name,spec)
        for share in (.05,.1,.25,.5):
            rows.append(compare(base[:int(len(base)*share)],f'e10/{ds}/{name}/share{share}'))
    # E11 changes the tail, not these learning prefixes; include actual inputs explicitly.
    for ds in ('mawi2021_flow','mawi2022_flow','caida_flow','caida'):
        s,order,paths=setup(ds);inputs.update({str(p.relative_to(BLOOM)):digest(p) for p in paths})
        base=stream(s,order,'drift',None if ds.endswith('_flow') else ('zipf',100000,1.0))
        rows.append(compare(base[:len(base)//4],f'e11/{ds}'))
    # Paper-source once AND Zipf inputs reused by round8/13.
    for ds in ('paper_url','paper_cod'):
        for name in ('once','zipf'):
            p=WR/f'round8_paper_data/inputs/{ds}/{name}_learn.npy'
            inputs[str(p.relative_to(BLOOM))]=digest(p)
            rows.append(compare(np.load(p,mmap_mode='r'),f'round8+13/{ds}/{name}'))
    # Main-setting full-construction fixtures; RA6 worker compresses distinct IDs locally.
    for ds in ('cod','url','caida','shalla','caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow'):
        p=WR/f'round7_original_e2e/inputs/{ds}/learn.npy'
        inputs[str(p.relative_to(BLOOM))]=digest(p)
        meta=json.loads(p.with_name('meta.json').read_text());assert digest(p)==meta['learn_sha256']
        learn=np.load(p);local=np.searchsorted(np.unique(learn),learn).astype(np.int64)
        rows.append(compare(local,f'round7+14/{ds}/compressed_learning'))
    # Prior E5 scaling: actual stored settings/lengths/pools, not approximate common sizes.
    s,order,paths=setup('caida');inputs.update({str(p.relative_to(BLOOM)):digest(p) for p in paths})
    seen=set()
    for var in ('learning','keys','candidates'):
        p=WR/f'round6_bucket/results/e5/{var}.json';inputs[str(p.relative_to(BLOOM))]=digest(p)
        for record in json.loads(p.read_text()):
            key=(record['L'],record['pool'])
            if key in seen:continue
            seen.add(key)
            base=stream(s,order,'e5',('zipf',record['pool'],1.0),queries=4*record['L'])
            row=compare(base[:record['L']],f'e5/{var}/L{record["L"]}/pool{record["pool"]}')
            assert row['distinct_keys']==record['distinct_learning_keys']
            rows.append(row)
    # New1M–100M curve, including its separate100K pilot. Input hash ties to round15.
    p=WR/'round15_learning_scaling_v2/inputs/learning.npy'
    meta=json.loads((p.parent/'manifest.json').read_text());assert digest(p)==meta['file_sha256']
    inputs[str(p.relative_to(BLOOM))]=digest(p);data=np.load(p,mmap_mode='r')
    for L in (100000,1000000,2000000,5000000,10000000,20000000,50000000,100000000):
        learn=data[:L];assert ah(learn)==meta['prefix_sha256'][str(L)]
        rows.append(compare(learn,f'round15/L{L}'))
    # TCP-only inputs also used by RA6-Z; source pool registration occurs in B.load_setup.
    tcp=json.loads((WR/'round18_gt_audit/results/tcp_supplement.json').read_text())
    for old in tcp['streams']:
        s,order,paths=setup(old['dataset']);inputs.update({str(p.relative_to(BLOOM)):digest(p) for p in paths})
        base=stream(s,order,'真实轨迹',None);assert ah(base)==old['base_stream_sha256']
        rows.append(compare(base[:len(base)//4],f'tcp+round17/{old["dataset"]}',old['original_rate_sha256']))
    aliases=dict(query_sqlite='round6 e789 and round5 e4 use the original25%-learning main streams; covered by main audits (not a new round12 SQLite generator)',
                 cost_audit='round12 audit_costs only aggregates stored round8 timings, no estimator execution',
                 warm='round6 warm6 uses the same original main learning streams',
                 zero_tree='round17 uses original main/TCP learning streams already covered',
                 removed_round16='Not restored or included in the public repair bundle; respects user-deleted publication history')
    save(output,dict(status='complete',streams=rows,inputs=inputs,aliases=aliases,
                     changed=[r['label'] for r in rows if not r['rate_bit_equal']]))
    print(f'EXTRA AUDIT COMPLETE: {len(rows)} actual learning inputs, changed {sum(not r["rate_bit_equal"] for r in rows)}',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=(*A.ALL,'extras'),required=True);a=p.parse_args()
    check_frozen()
    extras() if a.dataset=='extras' else main_dataset(a.dataset)
    check_frozen()
