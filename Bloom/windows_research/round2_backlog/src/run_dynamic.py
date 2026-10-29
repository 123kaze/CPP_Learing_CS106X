"""Sequential dynamic membership inserts: invalidate -> BF/index -> publish."""
import time,json
import numpy as np
import engine as E
import live_pipeline as L

def run():
    setup,scores,safe=E.load('url');_,_,X,_=E.C.load_dataset('url')
    setup.y=setup.y.copy();setup.member_hashes=setup.member_hashes.copy()
    c=E.build(setup,scores,8,64,.2);exe=L.Executable(setup,X,c,0)
    rng=np.random.default_rng(1017);testrows=np.flatnonzero(setup.split['neg_test'])
    warm=rng.choice(testrows,50000,replace=True);exe.batch(warm)
    q=exe.layout
    cached=[]
    for x in rng.permutation(len(setup.h1q)):
        if E.F.lookup(exe.slab,setup.h1q[x],q['qbits'],q['rbits'],q['slot_bits'],q['ways'],q['policy_code']):cached.append(int(x))
        if len(cached)>=1000:break
    candidates=list(dict.fromkeys(cached+list(map(int,rng.permutation(len(setup.h1q))))))[:1000]
    promoted=testrows[np.array(candidates)];hashes=setup.h1q[np.array(candidates)]
    mixed=rng.choice(testrows,200000,replace=True)
    mixed[::2]=rng.choice(promoted,len(mixed[::2]),replace=True)
    original_members=np.flatnonzero(setup.y);mixed[::10]=rng.choice(original_members,len(mixed[::10]),replace=True)
    invalidation=[];bf_times=[];index_times=[];removed=0;pass_promotions=0
    fp=fn=neg=0;initial_index_bytes=setup.member_hashes.nbytes
    # Warm all signatures on a discarded cache; never mutate publication order.
    E.F.invalidate(exe.slab,np.uint64(0),q['qbits'],q['rbits'],q['slot_bits'],q['ways'])
    for position,row in enumerate(mixed):
        if position%200==0:
            j=position//200;h=hashes[j];global_row=int(promoted[j])
            started=time.perf_counter_ns();removed+=E.F.invalidate(exe.slab,h,q['qbits'],q['rbits'],q['slot_bits'],q['ways']);invalidation.append(time.perf_counter_ns()-started)
            st=c['structure'];g=int(np.searchsorted(st.cuts,scores[c['trees']][global_row],side='right'))
            started=time.perf_counter_ns()
            if st.kind[g]==E.C.BF:
                E.R.packed_build(np.array([h],np.uint64),np.array([g],np.int32),st.bf_off,st.m,st.k,st.bits)
            elif st.kind[g]==E.C.EMPTY:st.kind[g]=E.C.PASS;pass_promotions+=1
            bf_times.append(time.perf_counter_ns()-started)
            started=time.perf_counter_ns();at=np.searchsorted(setup.member_hashes,h);setup.member_hashes=np.insert(setup.member_hashes,at,h);index_times.append(time.perf_counter_ns()-started)
            setup.y[global_row]=True # Publish only after all three preceding steps.
            accepted,_,_,_=exe.probe(global_row);assert accepted,'new member rejected after publication'
        accepted,h,_,_=exe.probe(row)
        if not setup.y[row]:neg+=1
        if accepted and not setup.y[row]:fp+=1;exe.insert(h)
        elif not accepted and setup.y[row]:fn+=1
    check=np.concatenate([promoted,original_members])
    verification=exe.batch(check);assert verification[2]==0 and fn==0
    assert removed>0,'Dynamic test must invalidate real cached conflicts'
    out=dict(completed=True,dataset='url',preset_trees=8,preset_frac=.2,budget_kib=64,queries=len(mixed),inserted_members=1000,
             original_cached_targets=len(cached),removed_cache_records=removed,false_negatives=fn,final_member_checks=len(check),full_final_member_verification=True,
             false_positives=fp,negative_queries=neg,filter_state_bytes=c['structure'].used_bytes,
             initial_member_index_bytes=initial_index_bytes,final_member_index_bytes=setup.member_hashes.nbytes,
             empty_regions_promoted_to_pass=pass_promotions,
             invalidation_median_ns=float(np.median(invalidation)),invalidation_p95_ns=float(np.quantile(invalidation,.95)),
             bf_update_median_ns=float(np.median(bf_times)),index_maintenance_median_ns=float(np.median(index_times)),
             scope='Actual URL keys promoted to members; sequential publication, not concurrent atomicity; NumPy sorted-index maintenance is additional memory/cost')
    E.save(E.ROOT/'results'/'dynamic_members.json',out);print(json.dumps(out),flush=True)
if __name__=='__main__':run()
