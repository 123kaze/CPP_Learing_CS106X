"""Historical MAWI allocation audit; future-length features are not main results."""
import json,numpy as np
import engine as E
E.C.CACHE=E.ROOT.parent/'cache'
setup=E.R.load_setup('mawi2021_flow');scores=E.R.scores_for(setup)
stream=E.C.load_flow_trace(setup);tail=stream[len(stream)//4:]
frequencies=np.bincount(tail,minlength=len(setup.h1q));rows=[];sets={}
for reserve in (5128,0):
    for kib in (40,48,64):
        candidates=[]
        for t in E.R.GAMA_TREES:
            st=E.R.structure(setup,scores,t,kib*1024,0,sketch_bytes=reserve)
            if st is not None:candidates.append((st.est_fpr,t,st))
        est,t,st=min(candidates,key=lambda x:x[:2])
        keys=np.flatnonzero(st.fp_static&(frequencies>0))
        order=keys[np.argsort(-frequencies[keys],kind='stable')]
        total=int(frequencies[keys].sum())
        top=[dict(query_id=str(int(setup.q_ids[x])),hash=str(int(setup.h1q[x])),count=int(frequencies[x]),
                  source='PASS' if st.in_pass_q[x] else 'BF') for x in order[:20]]
        rows.append(dict(budget_kib=kib,sketch_reserved_bytes=reserve,trees=t,estimated_validation_fpr=est,
                         evaluation_queries=len(tail),fp_total=total,distinct_fp_keys=len(keys),
                         fp_pass=int(frequencies[keys[st.in_pass_q[keys]]].sum()),
                         top1_fraction=(top[0]['count']/total if total else 0),top20=top,
                         physical_state_bytes=st.used_bytes))
        sets[reserve,kib]=set(map(int,keys))
overlap=[dict(sketch_reserved_bytes=s,budget_a=48,budget_b=64,
              shared_keys=len(sets[s,48]&sets[s,64]),new_at64=len(sets[s,64]-sets[s,48])) for s in (5128,0)]
E.save(E.ROOT/'results'/'F4_mawi_hotspots.json',dict(rows=rows,overlaps=overlap,
       scope='Historical five-feature MAWI representation only; address-only main evaluation is separate',
       explanation='Validation deduplicated FPR is optimized, not weighted trace FPR. Tree/allocation changes and remapped Bloom bits can expose a heavily repeated key even as estimated FPR falls. Top-key counts quantify whether this occurs.'))
print(json.dumps(dict(rows=[{k:v for k,v in r.items() if k!='top20'} for r in rows],overlap=overlap),indent=2),flush=True)
