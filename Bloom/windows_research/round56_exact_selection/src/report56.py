"""Require all three serial repetitions; no cherry-picking the fastest observation."""
import sys,csv,statistics
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common56 import *


def main():
    freeze_check(inputs=True);raw=[];summ=[];pairs=[]
    expected={f'{ds}_{k}_rep{rep}_{m}.json' for ds,k in SETTINGS for rep in range(REPS) for m in METHODS}
    assert {p.name for p in (ROOT/'results/main').glob('*.json')}==expected
    for ds,k in SETTINGS:
        _,old=reference(ds,k)
        by={}
        for m in METHODS:
            rr=[]
            for rep in range(REPS):
                r=read(ROOT/f'results/main/{ds}_{k}_rep{rep}_{m}.json')
                assert r['status']=='complete' and r['regression55'] and not r['pilot'] and r['method']==m and r['rep']==rep
                check_regression(r['selected'],next(x for x in old['rows'] if x['method']==m))
                assert r['learning_sha']==old['learning_sha'] and r['base_tail_sha']==old['base_tail_sha']
                assert all(v=='1' for v in r['native_threads'].values()) and r['peak_rss_bytes']<8*1024**3
                raw.append(dict(dataset=ds,budget_kib=k,method=m,rep=rep,selection_s=r['selection']['selection_s'],selection_cpu_s=r['selection']['selection_cpu_s'],warmup_s=r['warmup_s'],stream_generation_s=r['stream_generation_s'],verification_s=r['verification_s'],worker_s=r['worker_s'],peak_rss_bytes=r['peak_rss_bytes'],FP=r['selected']['fp'],trees=r['selected']['trees'],frac=r['selected']['frac']))
                rr.append(r)
            times=[r['selection']['selection_s'] for r in rr]
            by[m]=dict(median_s=statistics.median(times),min_s=min(times),max_s=max(times),reps_s=times)
            summ.append(dict(dataset=ds,budget_kib=k,method=m,**by[m],learning_queries=rr[0]['learning_queries'],tail_queries=rr[0]['tail_queries'],state=rr[0]['state'],count_rate_physical_bytes=rr[0]['selection'].get('count_rate_physical_bytes'),cpu_s=[r['selection']['selection_cpu_s'] for r in rr]))
        pairs.append(dict(dataset=ds,budget_kib=k,Gama_s=by['Gama']['median_s'],Replay_s=by['Replay']['median_s'],RA6_s=by['RA6']['median_s'],Replay_over_RA_speedup=by['Replay']['median_s']/by['RA6']['median_s'],paired_rep_speedups=[a/b for a,b in zip(by['Replay']['reps_s'],by['RA6']['reps_s'])]))
    for name,rows in (('rows.csv',raw),('summary.csv',summ),('paired.csv',pairs)):
        fields=sorted(set().union(*(r.keys() for r in rows)))
        with (ROOT/'results'/name).open('x',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
            for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in r.items()})
    save(ROOT/'results/verification.json',dict(status='passed',formal_workers=len(raw),settings=len(pairs),reps=3,all_regression_budget_FN_index_checks=True,summary=pairs,
         limitation='Current full-pool implementation, model/scoring reused. Not end-to-end construction, not service query latency, not a lower bound on optimized Replay. Serial workers do not exclude all unrelated OS/user workloads.'))
    text=['# 第56轮：exact-key独立串行选择成本','','每方法每设置3个独立worker；同输入完整warmup一次后计选择，包含learning预处理、候选构建与选择，排除共同数据/模型准备和选择后验证。','',
          '| 设置 | Gama(s) | Replay(s) | RA6(s) | Replay/RA6 |','|---|---:|---:|---:|---:|']
    for r in pairs:text.append(f"| {r['dataset']} {r['budget_kib']} | {r['Gama_s']:.4f} | {r['Replay_s']:.4f} | {r['RA6_s']:.4f} | {r['Replay_over_RA_speedup']:.3f} |")
    text+=['','按各方法3次中位时间作比，全部rep见CSV；小于1意味着RA更慢，不能删去。','',
           '时间只支持当前第55轮full-pool研究实现。原round15的local-key优化Replay未迁移，本轮不是任意优化Replay的速度下界；不据此宣称生产端到端加速。模型/分数复用，训练到ready的construction、在线query和scalability仍未完成。',
           '','状态区分trace逻辑view、离线driver实际保留的owning全流、假设紧凑learning副本、RA keys/counts/rate物理数组与主机rawkey输入。不能拿count状态比替代全进程RSS比。','']
    with (ROOT/'README.md').open('x') as f:f.write('\n'.join(text))
    print('SERIAL_SELECTION_VERIFIED 72 workers',flush=True)


if __name__=='__main__':main()
