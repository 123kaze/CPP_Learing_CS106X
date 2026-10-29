"""Periodic non-C calibration on retained past windows, with transition cost."""
import time,json,argparse,sys
import numpy as np
import engine as E
def segment(c,stream,setup,safe,data):
    spec=E.F.layout(c['cache_bytes'],c['prefix_bits'],c['policy'],c['ways'])
    return E.F.replay(stream,setup.h1q,safe,c['structure'].fp_static,data,spec['qbits'],spec['rbits'],spec['slot_bits'],
                      c['ways'],spec['policy_code'],spec['handbits'],2**62,0,1,
                      np.empty(0,np.uint64),np.empty(0,np.bool_),np.empty(0,np.bool_))
def identity(c):return c['trees'],c['cache_bytes'],c['policy'],c['prefix_bits'],c['ways']
def swap_bytes(a,b):
    arrays={};dictionaries={}
    for c in (a,b):
        st=c['structure']
        for x in list(st.model_arrays.values())+[st.cuts,st.kind,st.bf_off,st.m,st.k,st.bits]:arrays[id(x)]=x
        dictionaries[id(st.model_arrays)]=st.model_arrays
    return sum(sys.getsizeof(x) for x in arrays.values())+sum(sys.getsizeof(x) for x in dictionaries.values())+a['cache_bytes']+b['cache_bytes']
def run(ds,kib):
    dest=E.ROOT/'results'/f'recalibration_{ds}.json'
    if dest.exists() and json.loads(dest.read_text(encoding='utf-8'))['completed']:return
    setup,scores,safe=E.load(ds);cands=E.candidates(setup,scores,kib)
    zeros=[c for c in cands if c['frac']==0];gama=min(zeros,key=lambda c:c['structure'].est_fpr)
    probe=max((c for c in zeros if c['trees']<=48),key=lambda c:c['trees']);bins=E.BinMemo()
    obj=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],completed=False)
    done={r['seed'] for r in obj['rows']}
    for seed in range(5):
        if seed in done:continue
        stream=E.stream_for(setup,'向难负例漂移',('hard-drift',),'hard-drift',seed,10000000,gama['structure'])
        quarter=len(stream)//4
        first=E.rank(cands,E.measure(stream[:quarter],setup,probe['structure']),probe['structure'],len(stream)-quarter,quarter,bins)[0][-1]
        frozen=first;active=first
        frozen_data=E.F.allocate(E.F.layout(frozen['cache_bytes']));active_data=E.F.allocate(E.F.layout(active['cache_bytes']))
        intervals=[];total_frozen=total_periodic=0;peak=frozen['structure'].used_bytes
        for block in (1,2,3):
            start=block*quarter;stop=len(stream) if block==3 else (block+1)*quarter
            calibrate_seconds=rebuild_seconds=0.;changed=False
            if block>1:
                history=stream[start-quarter:start]
                t=time.perf_counter();stats=E.measure(history,setup,probe['structure'])
                selected=E.rank(cands,stats,probe['structure'],len(stream)-start,len(history),bins)[0][-1]
                calibrate_seconds=time.perf_counter()-t
                changed=identity(selected)!=identity(active)
                if changed:
                    t=time.perf_counter();replacement=E.build(setup,scores,selected['trees'],kib,selected['frac'])
                    rebuild_seconds=time.perf_counter()-t
                    peak=max(peak,swap_bytes(active,replacement))
                    active=replacement;active_data=E.F.allocate(E.F.layout(active['cache_bytes']))
            before=segment(frozen,stream[start:stop],setup,safe,frozen_data)
            after=segment(active,stream[start:stop],setup,safe,active_data)
            total_frozen+=int(before[0]);total_periodic+=int(after[0])
            intervals.append(dict(start_query=start,stop_query=stop,frozen_fp=int(before[0]),periodic_fp=int(after[0]),
                                  selected_trees=active['trees'],selected_frac=active['frac'],rebuild=changed,
                                  calibration_seconds=calibrate_seconds,rebuild_seconds=rebuild_seconds))
        obj['rows'].append(dict(dataset=ds,budget_kib=kib,seed=seed,queries=len(stream),evaluation_queries=len(stream)-quarter,
                                frozen_fp=total_frozen,periodic_fp=total_periodic,member_false_negatives=0,
                                retained_past_trace_bytes=quarter*8,temporary_sketch_bytes=5128+6*E.F.ARRAY_HEADER,
                                atomic_rebuild_peak_filter_state_bytes=peak,intervals=intervals,
                                swap_accounting='unique ndarray owners/model dictionaries plus both cache slabs; shared model arrays are not double-counted',
                                scope='Batch recalibration uses only a retained past quarter; no future query statistics. Double-buffer build peak and trace memory are additional costs, not same peak-memory deployment.'))
        E.save(dest,obj);print(f'RECALIB {ds} seed{seed} frozen={total_frozen} periodic={total_periodic}',flush=True)
    obj['completed']=True;E.save(dest,obj)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--budget',type=int,required=True);a=p.parse_args();run(a.dataset,a.budget)
