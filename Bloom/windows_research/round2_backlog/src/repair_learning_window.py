"""A1 fixed last50% holdout, retaining the original prefix-only grid choice."""
import json
import numpy as np
import engine as E
for ds,kib in [('cod',256),('caida',128),('caida_flow',24),('mawi2021_flow',24)]:
    path=E.ROOT/'results'/'ablations'/f'{ds}.json';obj=json.loads(path.read_text(encoding='utf-8'))
    assert obj['completed']
    if obj.get('A1_fixed_common_window'):continue
    archive=E.ROOT/'evidence'/'A1-original-variable-windows'/path.name;archive.parent.mkdir(parents=True,exist_ok=True)
    if not archive.exists():archive.write_bytes(path.read_bytes())
    setup,scores,safe=E.load(ds);cands=E.candidates(setup,scores,kib);zero=[c for c in cands if c['frac']==0]
    gama=min(zero,key=lambda c:c['structure'].est_fpr);probe=max((c for c in zero if c['trees']<=48),key=lambda c:c['trees'])
    old={(r['workload'],r['seed'],r['learning_fraction']):r for r in obj['rows'] if r['task']=='A1' and r['variant']=='grid'}
    specs={w[0]:w[1:] for w in E.workload_specs(len(setup.h1q))} if not ds.endswith('_flow') else {'真实轨迹':(None,'trace')}
    rows=[r for r in obj['rows'] if r['task']!='A1'];bins=E.BinMemo()
    for name,seed in obj['completed_cases']:
        spec,family=specs[name];stream=E.stream_for(setup,name,spec,family,seed,10000000,gama['structure'])
        start=len(stream)//2;tail=stream[start:];freq=np.bincount(tail,minlength=len(setup.h1q))
        for fraction in (.05,.1,.25,.5):
            n=int(len(stream)*fraction);stats=E.measure(stream[:n],setup,probe['structure'])
            model=E.rank(cands,stats,probe['structure'],len(tail),n,bins)[0][-1]
            previous=old[name,seed,fraction]
            grid=next(c for c in cands if c['trees']==previous['trees'] and c['frac']==previous['frac'])
            for label,c in [('model',model),('grid',grid),('Gama',gama)]:
                result=E.evaluate(c,tail,setup,safe,freq)
                row=E.row(c,result,ds,kib,name,seed,label,len(stream),n)
                row.update(task='A1',variant=label,learning_fraction=fraction,evaluation_start_query=start,
                           evaluation_queries=len(tail),fpr=result['fp']/len(tail),
                           unused_gap_queries=start-n,member_index_bytes=setup.member_hashes.nbytes,
                           grid_choice_reused_from_identical_learning_prefix=label=='grid',common_last50pct=True)
                rows.append(row)
        print('A1 FIXED COMMON WINDOW',ds,name,seed,flush=True)
    obj['rows']=rows;obj['A1_fixed_common_window']=True;E.save(path,obj);E.R._GSETUPS.clear()
