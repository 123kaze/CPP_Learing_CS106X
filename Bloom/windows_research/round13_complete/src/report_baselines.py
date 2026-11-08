"""Complete BF+cache coverage: original 1146 cases, TCP-only 16, MAWI24 4.

Round12 data are reused, never selectively dropped. Two cache formats are kept separate.
"""
import csv
import json
import math
from pathlib import Path
from statistics import median,mean
from collections import defaultdict

ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent
MAIN={'cod':(256,1024,4096),'caida':(128,256,1024,2048),'shalla':(256,1024,2048,4096),
      'url':(64,128,256),'caida_flow':(16,24,32,256),'mawi2020_flow':(16,24,32,128),
      'mawi2021_flow':(16,24,32,128),'mawi2022_flow':(16,24,32,128)}
PROBE='探测重放10%'


def load(folder,ds,kib,method):
    out={}
    p=folder/f'rows_{ds}_{kib}.csv'
    with p.open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['method']!=method:continue
            key=(r['workload'],int(r['seed']))
            assert key not in out,(p,key)
            assert r['dataset']==ds and int(r['budget_kib'])==kib
            out[key]=r
    assert out,(p,method)
    return out


def ratio(a,b):return (a+1)/(b+1)


def stats(rows):
    v=[ratio(r['ra_fp'],r['bfcache_fp']) for r in rows]
    assert v
    return dict(cases=len(rows),median=median(v),minimum=min(v),maximum=max(v),
                wins=sum(r['ra_fp']<r['bfcache_fp'] for r in rows),ties=sum(r['ra_fp']==r['bfcache_fp'] for r in rows),
                losses=sum(r['ra_fp']>r['bfcache_fp'] for r in rows),geometric_mean=math.exp(mean(map(math.log,v))))


def fmt(v):return f'{v:.3f}' if v>=.001 else f'{v:.2e}'


def main():
    done=json.loads((ROOT/'results/baseline_completion.json').read_text())
    assert done['status']=='complete' and done['bf_rows']==1600
    tcp=json.loads((WR/'round11_tcp/results/datasets.json').read_text())
    sets={**MAIN,**{ds:tuple(m['budgets_kib']) for ds,m in tcp.items()},'mawi2024_flow':(16,24,32,128)}
    rows=[]
    for ds,budgets in sets.items():
        cohort='main' if ds in MAIN else ('tcp' if ds in tcp else 'holdout_posthoc')
        for kib in budgets:
            if cohort=='main':
                r5dir=WR/'round5_dp/results';r6dir=WR/'round6_bucket/results/main'
                fpdir=WR/'round10_fpcache/results/main';gfdir=WR/'round10_fpcache/results/grid'
            elif cohort=='tcp':
                r5dir=WR/'round11_tcp/results/run5/results';r6dir=WR/'round11_tcp/results/run6/results/main'
                fpdir=WR/'round11_tcp/results/run10/results/main';gfdir=WR/'round11_tcp/results/grid10/results/grid'
            else:
                r5dir=WR/'round6_bucket/results/holdout/round5_methods';r6dir=WR/'round6_bucket/results/holdout'
                fpdir=ROOT/'results/holdout_fp64';gfdir=ROOT/'results/holdout_grid_fp64'
            control_root=WR/'round12_nomodel/results/main' if ds in ('cod','url','shalla') or cohort=='tcp' else ROOT/'results/baselines'
            gam=load(r5dir,ds,kib,'Gama');r4=load(r5dir,ds,kib,'RA4');oldgrid=load(r5dir,ds,kib,'LearnGrid')
            paired={}
            for mode in ('index','fp64'):
                suffix='' if mode=='index' else '-fp64'
                bf=load(control_root/mode,ds,kib,'BF'+suffix)
                bc=load(control_root/mode,ds,kib,'BF+ReplayCache'+suffix)
                ra=load(r6dir if mode=='index' else fpdir,ds,kib,'RA6'+suffix)
                grid=load(r5dir if mode=='index' else gfdir,ds,kib,'LearnGrid'+suffix)
                assert bf.keys()==bc.keys()==ra.keys()==gam.keys()==grid.keys()==r4.keys()==oldgrid.keys()
                assert len(bf)==(1 if ds.endswith('_flow') else (95 if ds=='caida' else 75))
                paired[mode]=bf
                for key,b in bc.items():
                    p=bf[key]
                    assert b['base_stream_sha256']==p['base_stream_sha256']
                    if key[0]!=PROBE:assert b['tail_stream_sha256']==p['tail_stream_sha256']
                    raw=r4[key]['fp_oracle'];ref=float(raw) if raw!='' else int(oldgrid[key]['fp_tail'])
                    n=int(b['tail_len'])
                    rows.append(dict(dataset=ds,budget_kib=kib,workload=key[0],seed=key[1],cache=mode,cohort=cohort,
                                     included=ref>=30,reference_fp=ref,bf_fp=int(p['fp_tail']),bfcache_fp=int(b['fp_tail']),
                                     ra_fp=int(ra[key]['fp_tail']),replay_fp=int(grid[key]['fp_tail']),gama_fp=int(gam[key]['fp_tail']),
                                     tail_len=n,ra_over_bfcache=ratio(int(ra[key]['fp_tail']),int(b['fp_tail'])),
                                     base_stream_sha256=b['base_stream_sha256']))
            for key in paired['index']:
                a,b=paired['index'][key],paired['fp64'][key]
                assert a['base_stream_sha256']==b['base_stream_sha256'] and a['fp_tail']==b['fp_tail']
    assert len(rows)==2332
    with (ROOT/'results/combined_baseline_rows.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary={}
    lines=['# 普通 BF＋缓存：补齐全数据覆盖', '',
           '原主表 1146 个案例、TCP-only 16 个、MAWI-24 4 个，两种缓存格式共 2332 个对齐案例。'
           '第十二轮的既有结果全部复用，本轮新增缺失的数据，不按结果挑选数据集。', '',
           'MAWI-24 的 BF＋缓存、RA6-fp64 和 Replay-fp64 是后续补测；不是新一轮独立验证。原 UDP/TCP 构造的现实性问题也不会因补齐基线而消失。', '',
           '比值 `(RA6 FP+1)/(BF+cache FP+1)` 小于 1 为 RA6 更好。主表去掉探测重放，并沿用旧参照 FP≥30 筛选；低计数的完整数据仍在 CSV。', '',
           '| 缓存 | 数据 | 纳入 | 排除 | 中位 | 最差 | 胜/平/负 |', '|---|---|---:|---:|---:|---:|---|']
    for mode in ('index','fp64'):
        for ds in (*MAIN,'all'):
            group=[r for r in rows if r['cohort']=='main' and r['cache']==mode and r['workload']!=PROBE and (ds=='all' or r['dataset']==ds)]
            eligible=[r for r in group if r['included']]
            s=stats(eligible);summary[f'{mode}/{ds}']=dict(**s,excluded=len(group)-len(eligible))
            if ds=='all':assert len(group)==1076 and len(eligible)==748
            lines.append(f"| {mode} | {ds} | {s['cases']} | {len(group)-len(eligible)} | {fmt(s['median'])} | "
                         f"{fmt(s['maximum'])} | {s['wins']}/{s['ties']}/{s['losses']} |")
    for cohort,title in (('tcp','TCP-only（旧轨迹的新任务构造）'),('holdout_posthoc','MAWI-24（后续补测）')):
        lines += ['',f'## {title}', '', '| 缓存 | 数据 | KiB | BF＋缓存 | RA6 | Replay | RA6/BF＋缓存 |', '|---|---|---:|---:|---:|---:|---:|']
        for r in rows:
            if r['cohort']==cohort:
                lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {r['bfcache_fp']:,} | {r['ra_fp']:,} | "
                             f"{r['replay_fp']:,} | {fmt(r['ra_over_bfcache'])} |")
        for mode in ('index','fp64'):
            s=stats([r for r in rows if r['cohort']==cohort and r['cache']==mode]);summary[f'{cohort}/{mode}']=s
            lines.append(f"\n{mode}：中位 {fmt(s['median'])}，胜/平/负 {s['wins']}/{s['ties']}/{s['losses']}。")
    lines += ['', '## 探测重放（结构相关尾流，单列）', '']
    for mode in ('index','fp64'):
        s=stats([r for r in rows if r['cache']==mode and r['workload']==PROBE]);summary[f'probe/{mode}']=s
        lines.append(f"- {mode}：{s['cases']} 个案例，中位 {fmt(s['median'])}，最差 {fmt(s['maximum'])}，胜/平/负 {s['wins']}/{s['ties']}/{s['losses']}。")
    lines += ['', '本表不把共享模型的案例当成独立样本来宣称显著性；也不能将模型/分段表示相对 BF 的收益全部归给 RA6 的重新加权。']
    (ROOT/'results/baseline_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    (ROOT/'results/baseline_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Combined baseline report: 2332 aligned cache-specific cases, complete coverage.')


if __name__=='__main__':main()
