import argparse,time,json
import numpy as np
import engine as E
import learned_stacked as S
def run(ds,budgets,queries=10000000,seeds=5):
    setup,scores,safe=E.load(ds)
    out=E.ROOT/'results'/'stacked'/ds;out.mkdir(parents=True,exist_ok=True)
    specs=[('真实轨迹',None,'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    if ds.endswith('_flow'):seeds=1
    for kib in budgets:
        dest=out/f'{kib}.json';obj=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],infeasible=[],completed=False)
        if obj['completed']:continue
        zeros=[E.build(setup,scores,t,kib,0.) for t in E.R.GAMA_TREES];zeros=[c for c in zeros if c]
        gama=min(zeros,key=lambda c:c['structure'].est_fpr)
        done={(r['workload'],r['seed']) for r in obj['rows']+obj['infeasible']}
        for name,spec,family in specs:
            for seed in range(seeds):
                if (name,seed) in done:continue
                ts=time.perf_counter();stream=E.stream_for(setup,name,spec,family,seed,queries,gama['structure'])
                n=len(stream)//4
                result=S.choose(setup,scores,kib,gama['trees'],stream[:n])
                if result is None:obj['infeasible'].append(dict(workload=name,seed=seed,reason='side layers cannot fit'))
                else:
                    fp=result.pop('fp_static');base=result.pop('base')
                    assert result['state_bytes']<=kib*1024
                    count=int(fp[stream[n:]].sum())
                    obj['rows'].append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,method='LearnedStacked_LearnTune',
                                            evaluation_queries=len(stream)-n,learning_queries=n,fp_tail=count,fpr=count/(len(stream)-n),
                                            member_false_negatives=0,**result))
                E.save(dest,obj)
                print(f'stacked {ds}/{kib} {name} seed{seed} {time.perf_counter()-ts:.1f}s',flush=True)
        obj['completed']=True;E.save(dest,obj)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--budgets');a=p.parse_args()
    run(a.dataset,[int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset])
