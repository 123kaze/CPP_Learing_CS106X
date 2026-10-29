"""Five hash salts on development traces only; never five independent traces."""
import json,time
import numpy as np
import engine as E
def run(ds):
    setup,scores,_=E.load(ds)
    stream=E.C.load_flow_trace(setup);n=len(stream)//4;learn=stream[:n];tail=stream[n:]
    dest=E.ROOT/'results'/'hash_sensitivity'/f'{ds}.json'
    obj=json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[],completed_cases=[],completed=False)
    for seed in range(1,6):
        salt=np.uint64((int(E.C.H1_SALT)+seed*0x9e3779b97f4a7c15)&((1<<64)-1))
        h=E.C.splitmix64(setup.ids^salt)
        setup.h1m=h[setup.y];setup.h1q=h[setup.split['neg_test']];setup.member_hashes=np.sort(setup.h1m)
        safe=E.CC.safe_prefix_lengths(setup.member_hashes,setup.h1q)
        E.R._GSETUPS.clear()
        for kib in (16,24,32):
            if [seed,kib] in obj['completed_cases']:continue
            cands=E.candidates(setup,scores,kib);zeros=[c for c in cands if c['frac']==0]
            gama=min(zeros,key=lambda c:c['structure'].est_fpr)
            probe=max((c for c in zeros if c['trees']<=48),key=lambda c:c['trees'])
            stats=E.measure(learn,setup,probe['structure']);ranks=E.rank(cands,stats,probe['structure'],len(tail),n,E.BinMemo())
            grid,_,seconds,_=E.exact_grid(ranks,learn,setup,safe,track48=False)
            plains=[E.build_plain(setup,kib,f) for f in E.FRACS];plain,_,_,_=E.exact_grid(plains,learn,setup,safe,track48=False)
            model=ranks[0][-1];ski=E.build(setup,scores,model['trees'],kib,model['frac'],admit=2)
            for name,c in [('Gama',gama),('StreamModel',model),('LearnGrid',grid),('BFCacheGrid',plain),('SkiQFAdmission2',ski)]:
                result=E.evaluate(c,tail,setup,safe)
                row=E.row(c,result,ds,kib,'真实轨迹',seed,name,len(stream),n)
                row.update(hash_salt_hex=hex(int(salt)),member_index_bytes=setup.member_hashes.nbytes,
                           replication_scope='Hash realization sensitivity on one fixed trace, not independent workload traces')
                obj['rows'].append(row)
            obj['completed_cases'].append([seed,kib]);E.save(dest,obj)
            print('HASH SENSITIVITY',ds,seed,kib,flush=True)
    obj['completed']=True;E.save(dest,obj)
if __name__=='__main__':
    for ds in ('caida_flow','mawi2021_flow'):run(ds)
