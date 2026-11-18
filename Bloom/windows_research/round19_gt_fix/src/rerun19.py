"""Affected-case adapter: scoped counter hook + original frozen algorithms.

Explicit new outputs avoid frozen-driver skip/overwrite logic and stale main-table
assertions. Old executions must reproduce the archive; repaired executions may
change and are compared, never forced to agree. No original source is modified.
"""
from entry19 import *
import argparse
import csv
import time
import numpy as np
from contextlib import nullcontext
sys.path.insert(0,str(WR/'round6_bucket/src'))
import ra6
import warm6
sys.path.insert(0,str(WR/'round5_dp/src'))
import run5
E5,RA=ra6.E5,ra6.RA
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import baseline as BF


def archive(ds,kib,mode):
    folders=[WR/'round5_dp/results',WR/'round6_bucket/results/main'] if mode=='index' else [WR/'round10_fpcache/results/main']
    out={}
    for folder in folders:
        p=folder/f'rows_{ds}_{kib}.csv'
        with p.open() as f:
            for r in csv.DictReader(f):out[r['workload'],int(r['seed']),r['method']]=r
    return out


def structure_digest(c,setup,scores):
    st=c['structure'];td=E5.tree(setup,scores,c['trees'])
    reg=E5.D.region_of_segment(st.b)
    off=np.concatenate([[0],np.cumsum(st.m)]).astype(np.int64)
    bits=np.zeros(st.filter_bytes,np.uint8)
    E5.R.packed_build(setup.h1m,reg[td.seg_m].astype(np.int32),off,st.m,st.k,bits)
    return dict(trees=c['trees'],frac=c['frac'],cache_bytes=c['cache_bytes'],total_bytes=st.used_bytes,
                payload_sha256=ah(bits),static_flags_sha256=ah(st.fp_static),
                region_bounds_sha256=ah(st.b),region_hashcounts_sha256=ah(st.k))


def measured(c,tail,setup,safe,scores,pred=None):
    out=structure_digest(c,setup,scores)
    out['fp']=int(E5.evaluate(c,tail,setup,safe)['fp'])
    out['predicted_fp']=None if pred is None else float(pred)
    assert out['total_bytes']<=c['structure'].budget_bytes
    return out


def selections(setup,scores,learn,kib,H,patched_mode,mode,seed):
    with patched() if patched_mode else nullcontext():
        lm=ra4.summarize(learn,True)
        multi=ra6.select6_multi(setup,scores,lm,kib,H,ks=(3,5,10) if mode=='index' else (5,))
        results={f'RA6-top{k}' if k!=5 else 'RA6':(c,i['predicted_fp']) for k,(c,i) in multi.items()}
        table=None
        if mode=='index':
            extra={'noGT':(ra4.summarize(learn,False),RA.Config(new_mix=0.,gt=False)),
                   'mix0.5':(lm,RA.Config(new_mix=.5))} if seed==0 else None
            c,info=RA.select(setup,scores,lm,kib,H,run5.MAIN,keep_table=True,extra_predictors=extra)
            table=info['table'];results['RA4']=(c,info['predicted_fp'])
            for name,cfg in run5.ABLATIONS.items():
                lmv=lm if cfg.gt else ra4.summarize(learn,False)
                c,info=RA.select(setup,scores,lmv,kib,H,cfg)
                results[name]=(c,info['predicted_fp'])
    return results,table,lm


def main(ds,mode):
    output=ROOT/f'results/rerun_{ds}_{mode}.json';assert not output.exists()
    E5.K=BF.CACHES[mode]
    warm6.K=E5.K
    affected=json.loads((WR/'round18_gt_audit/results/affected_cases.json').read_text())
    jobs=[r for r in affected if r['dataset']==ds];assert jobs
    check_frozen();setup,scores,safe=E5.load(ds)
    name=jobs[0]['workload'];seed=jobs[0]['seed'];assert all((r['workload'],r['seed'])==(name,seed) for r in jobs)
    base=E5.base_stream(setup,name,dict(E5.workload_specs(len(setup.h1q)))[name],seed)
    n=len(base)//4;learn,tail=base[:n],base[n:]
    original=ORIGINAL_SUMMARIZE(learn,True)
    assert ah(original.rate)==jobs[0]['original_rate_sha256']
    with patched():fixed=ra4.summarize(learn,True)
    assert (fixed.rate>original.rate).sum()==1
    out=dict(status='running',dataset=ds,cache=mode,base_stream_sha256=ah(base),cases=[])
    for job in sorted(jobs,key=lambda r:r['budget_kib']):
        kib=job['budget_kib'];refs=archive(ds,kib,mode)
        start=time.perf_counter()
        old,ot,olm=selections(setup,scores,learn,kib,len(tail),False,mode,seed)
        new,nt,nlm=selections(setup,scores,learn,kib,len(tail),True,mode,seed)
        case=dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,cache=mode,methods={},candidate_changes=[])
        for method,(oc,op) in old.items():
            nc,npred=new[method]
            a=measured(oc,tail,setup,safe,scores,op);b=measured(nc,tail,setup,safe,scores,npred)
            archived_name=method if mode=='index' else 'RA6-fp64'
            ref=refs[name,seed,archived_name]
            assert (a['fp'],a['trees'],a['cache_bytes'],a['total_bytes'])==(int(ref['fp_tail']),int(ref['trees']),int(ref['cache_alloc_bytes']),int(ref['total_bytes']))
            if ref.get('pred_fp'):
                want=float(ref['pred_fp']);assert abs(a['predicted_fp']-want)<=1e-9*max(1,abs(want)),(method,'old prediction mismatch')
            flags_equal=np.array_equal(oc['structure'].fp_static,nc['structure'].fp_static)
            if flags_equal and a['cache_bytes']==b['cache_bytes']:assert a['fp']==b['fp']
            case['methods'][method]=dict(old=a,repaired=b,same_configuration=all(a[k]==b[k] for k in ('trees','frac','cache_bytes','total_bytes')),
                                         identical_payload=a['payload_sha256']==b['payload_sha256'],identical_static_flags=flags_equal,
                                         same_fp=a['fp']==b['fp'],old_matches_archive=True)
        if mode=='index':
            oc=old['RA6'][0];nc=new['RA6'][0]
            with (WR/f'round6_bucket/results/warm/rows_{ds}_{kib}.csv').open() as f:
                ref=next(r for r in csv.DictReader(f) if r['workload']==name and int(r['seed'])==seed)
            ow=warm6.warm_fp(oc,learn,tail,setup,safe);nw=warm6.warm_fp(nc,learn,tail,setup,safe)
            assert ow==int(ref['fp_tail'])
            case['warm']=dict(old_fp=ow,repaired_fp=nw,same_fp=ow==nw)
            # E3 all-candidate prediction/quality (seed0) or rank top10 (seed2).
            if seed==0:
                p=WR/f'round5_dp/results/e3_{ds}_{kib}.jsonl'
                with p.open() as f:ref=next(json.loads(line) for line in f if (json.loads(line)['workload'],json.loads(line)['seed'])==(name,seed))
                prior={(r['trees'],r['frac']):r for r in ref['candidates']}
                keys=list(prior)
            else:
                p=WR/f'round6_bucket/results/e3_seeds/{ds}_{kib}.json'
                ref=next(r for r in json.loads(p.read_text()) if (r['workload'],r['seed'])==(name,seed))
                prior={(r[0],r[1]):dict(pred=r[2],bucket_pred=r[3],measured=r[4]) for r in ref['rank_rows']}
                old_top=sorted(ot,key=lambda r:(r['pred'],r['trees'],r['frac']))[:10]
                new_top=sorted(nt,key=lambda r:(r['pred'],r['trees'],r['frac']))[:10]
                assert [(r['trees'],r['frac']) for r in old_top]==list(prior)
                case['rank_old_top10']=[(r['trees'],r['frac']) for r in old_top]
                case['rank_repaired_top10']=[(r['trees'],r['frac']) for r in new_top]
                keys=list(dict.fromkeys([*prior,*[(r['trees'],r['frac']) for r in new_top]]))
            old_table={(r['trees'],r['frac']):r for r in ot};new_table={(r['trees'],r['frac']):r for r in nt}
            for key in keys:
                a,b=old_table[key],new_table[key]
                for row in (a,b):assert np.isfinite(row['pred'])
                ar=prior.get(key)
                if ar:
                    assert abs(a['pred']-ar['pred'])<=1e-9*max(1,abs(ar['pred']))
                oc=E5.build(setup,scores,a['trees'],kib,a['frac'],weights=a['weights'],cache_bytes=a['cache_bytes'],slots=a['slots'])
                nc=E5.build(setup,scores,b['trees'],kib,b['frac'],weights=b['weights'],cache_bytes=b['cache_bytes'],slots=b['slots'])
                same=np.array_equal(oc['structure'].fp_static,nc['structure'].fp_static) and oc['cache_bytes']==nc['cache_bytes']
                ofp=int(ar['measured']) if ar else int(E5.evaluate(oc,tail,setup,safe)['fp'])
                nfp=ofp if same else int(E5.evaluate(nc,tail,setup,safe)['fp'])
                td=E5.tree(setup,scores,a['trees'])
                ob=ra6.bucket_prediction(setup,olm,td,oc,len(tail),a['seg_fpr_pred'])
                nb=ra6.bucket_prediction(setup,nlm,td,nc,len(tail),b['seg_fpr_pred'])
                if ar and 'bucket_pred' in ar:assert abs(ob-ar['bucket_pred'])<=1e-9*max(1,abs(ar['bucket_pred']))
                row=dict(trees=a['trees'],frac=a['frac'],old_pred=a['pred'],repaired_pred=b['pred'],old_bucket_pred=ob,repaired_bucket_pred=nb,
                         old_fp=ofp,repaired_fp=nfp,identical_static_flags_and_cache=same,
                         repaired_fp_source='archived value justified by identical full-pool flags/cache/stream' if same else 'new frozen tail replay',
                         old_fullassoc_pred=a['pred_fullassoc'],repaired_fullassoc_pred=b['pred_fullassoc'],
                         old_other_predictions=a['preds_other'],repaired_other_predictions=b['preds_other'])
                case['candidate_changes'].append(row)
        case['diagnostic_wall_s']=time.perf_counter()-start
        out['cases'].append(case);save(output,out)
        print(f'RECHECKED {ds}/{kib} {mode}: RA6 FP {case["methods"]["RA6"]["old"]["fp"]}->{case["methods"]["RA6"]["repaired"]["fp"]}; methods={len(case["methods"])} E3={len(case["candidate_changes"])}',flush=True)
    check_frozen();out['status']='complete';save(output,out)
    print(f'COMPLETE affected rerun {ds} {mode}: {len(out["cases"])} cases',flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',choices=('cod','url','caida','shalla'),required=True)
    p.add_argument('--cache',choices=('index','fp64'),required=True);a=p.parse_args();main(a.dataset,a.cache)
