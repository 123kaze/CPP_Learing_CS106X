"""Real upstream AdaptiveQF; QF heap and reverse map measured separately."""
from pathlib import Path
import argparse,subprocess,json,time
import numpy as np
import engine as E
def wsl(path):return '/mnt/'+str(path.drive[0]).lower()+str(path)[2:].replace('\\','/')
def run(ds,kib):
    setup,scores,safe=E.load(ds)
    tmp=E.ROOT/'tmp'/('aqf_'+ds);tmp.mkdir(parents=True,exist_ok=True)
    setup.h1m.tofile(tmp/'members.bin');setup.h1q.tofile(tmp/'queries.bin')
    folder=E.ROOT/'results'/'aqf';folder.mkdir(exist_ok=True)
    dest=folder/f'{ds}_{kib}.json'
    obj=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],completed=False)
    if obj['completed']:return
    done={(r['workload'],r['seed']) for r in obj['rows']}
    zeros=[E.build(setup,scores,t,kib,0.) for t in E.R.GAMA_TREES];zeros=[c for c in zeros if c]
    gama=min(zeros,key=lambda c:c['structure'].est_fpr)
    specs=[('真实轨迹',None,'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    seeds=1 if ds.endswith('_flow') else 5
    for name,spec,family in specs:
        for seed in range(seeds):
            if (name,seed) in done:continue
            start=time.perf_counter();stream=E.stream_for(setup,name,spec,family,seed,10000000,gama['structure']);n=len(stream)//4
            stream[n:].tofile(tmp/'stream.bin')
            command=['wsl','-d','Ubuntu-24.04','--',wsl(E.ROOT/'external'/'aqf_driver'),str(kib*1024),
                     wsl(tmp/'members.bin'),wsl(tmp/'queries.bin'),wsl(tmp/'stream.bin'),'0',wsl(tmp/'output.json')]
            r=subprocess.run(command,capture_output=True)
            (tmp/'last-native.log').write_bytes(r.stdout+b'\n'+r.stderr)
            if r.returncode:raise RuntimeError(r.stderr[-2000:])
            result=json.loads((tmp/'output.json').read_text())
            if result['feasible']:
                assert result['fn_before']==result['fn_after']==0
                assert result['filter_allocated_bytes']<=kib*1024
            obj['rows'].append(dict(dataset=ds,budget_kib=kib,workload=name,seed=seed,
                                    method='UpstreamAdaptiveQF',evaluation_queries=len(stream)-n,
                                    fpr=result.get('fp_tail',0)/(len(stream)-n) if result['feasible'] else None,
                                    gama_fp=int(gama['structure'].fp_static[stream[n:]].sum()),
                                    gama_trees=gama['trees'],cold_suffix=True,elapsed_seconds=time.perf_counter()-start,**result))
            E.save(dest,obj);print(f'AQF {ds}/{kib} {name} seed{seed} {time.perf_counter()-start:.1f}s feasible={result["feasible"]}',flush=True)
    obj['completed']=True;E.save(dest,obj)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--dataset',required=True);p.add_argument('--budget',type=int,required=True);a=p.parse_args();run(a.dataset,a.budget)
