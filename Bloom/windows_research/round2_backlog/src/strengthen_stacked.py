"""Complete already-run learning grids with the fair zero-layer fallback."""
import json,time
import numpy as np
import engine as E
for ds in ('cod','caida','shalla','url','caida_flow','mawi2021_flow'):
    setup,scores,safe=E.load(ds)
    for path in sorted((E.ROOT/'results'/'stacked'/ds).glob('*.json')):
        obj=json.loads(path.read_text(encoding='utf-8'))
        assert obj['completed']
        if obj.get('zero_fallback_rechecked'):continue
        kib=int(path.stem)
        archive=E.ROOT/'evidence'/'stacked-before-zero-fallback'/ds/path.name;archive.parent.mkdir(parents=True,exist_ok=True)
        if not archive.exists():archive.write_bytes(path.read_bytes())
        zeros=[E.build(setup,scores,t,kib,0.) for t in E.R.GAMA_TREES];zeros=[c for c in zeros if c]
        gama=min(zeros,key=lambda c:c['structure'].est_fpr)
        specs={w[0]:w[1:] for w in E.workload_specs(len(setup.h1q))} if not ds.endswith('_flow') else {'真实轨迹':(None,'trace')}
        cases=[dict(row,was_infeasible=False) for row in obj['rows']]+[dict(row,was_infeasible=True) for row in obj['infeasible']]
        output=[]
        for row in cases:
            spec,family=specs[row['workload']]
            stream=E.stream_for(setup,row['workload'],spec,family,row['seed'],10000000,gama['structure'])
            n=len(stream)//4;validation=stream[n//2:n]
            start=time.perf_counter();vfp=int(gama['structure'].fp_static[validation].sum());seconds=time.perf_counter()-start
            old=min((p['validation_fp'] for p in row.get('grid',[])),default=2**62)
            if row['was_infeasible'] or vfp<=old:
                count=int(gama['structure'].fp_static[stream[n:]].sum())
                grid=row.get('grid',[])
                row=dict(dataset=ds,budget_kib=kib,workload=row['workload'],seed=row['seed'],method='LearnedStacked_LearnTune',
                         evaluation_queries=len(stream)-n,learning_queries=n,fp_tail=count,fpr=count/(len(stream)-n),member_false_negatives=0,
                         frac=0.,b2=0.,selected_trees=gama['trees'],state_bytes=gama['structure'].used_bytes,
                         learning_seconds=row.get('learning_seconds',0)+seconds,
                         layers=dict(side_bytes=0,negative_bytes=0,positive_bytes=0,known_negatives=0),grid=grid)
            row.pop('was_infeasible',None)
            row['zero_fallback_validation_fp']=vfp;row['zero_fallback_recheck_seconds']=seconds
            output.append(row)
        obj['rows']=sorted(output,key=lambda r:(r['workload'],r['seed']));obj['infeasible']=[];obj['zero_fallback_rechecked']=True
        E.save(path,obj);print('ZERO FALLBACK CHECKED',ds,kib,len(output),flush=True)
    E.R._GSETUPS.clear()
