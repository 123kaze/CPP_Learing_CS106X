"""Strict complete-case report for the pre-specified no-model controls; no paper editing."""
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from statistics import mean, median

ROOT=Path(__file__).resolve().parents[1]
WR=ROOT.parent
BUDGETS={'cod':(256,1024,4096),'url':(64,128,256),'shalla':(256,1024,2048,4096)}
PROBE='探测重放10%'


def read_rows(folder, method, ds, kib):
    path=folder/f'rows_{ds}_{kib}.csv'
    out={}
    with path.open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            if r['method']!=method:
                continue
            key=(r['workload'],int(r['seed']))
            assert key not in out,(path,key)
            assert r['dataset']==ds and int(r['budget_kib'])==kib
            assert int(r['fp_tail'])>=0
            out[key]=r
    assert out,(path,method)
    return out


def ratio(a,b):
    return (a+1)/(b+1)


def fmt_ratio(value):
    return f'{value:.3f}' if value >= .001 else f'{value:.2e}'


def summarize(rows, numerator='ra_fp', denominator='bf_cache_fp'):
    values=[ratio(r[numerator],r[denominator]) for r in rows]
    if not values:
        return dict(n=0)
    return dict(n=len(rows),median=median(values),minimum=min(values),maximum=max(values),
                wins=sum(r[numerator]<r[denominator] for r in rows),
                ties=sum(r[numerator]==r[denominator] for r in rows),
                losses=sum(r[numerator]>r[denominator] for r in rows),
                geometric_mean=math.exp(mean(math.log(v) for v in values)))


def group(workload):
    if workload=='真实轨迹': return '真实轨迹'
    if workload==PROBE:return '探测重放'
    for label in ('1万','10万','全部'):
        if workload.endswith('-'+label):return label
    return '无重复'


def main():
    completion=json.loads((ROOT/'results/completion.json').read_text())
    assert completion['status']=='complete' and completion['rows']==3064
    tcp=json.loads((WR/'round11_tcp/results/datasets.json').read_text())
    budgets={**BUDGETS,**{d:tuple(m['budgets_kib']) for d,m in tcp.items()}}
    rows=[]
    for ds,bs in budgets.items():
        is_tcp=ds in tcp
        r5dir=WR/('round11_tcp/results/run5/results' if is_tcp else 'round5_dp/results')
        r6dir=WR/('round11_tcp/results/run6/results/main' if is_tcp else 'round6_bucket/results/main')
        r10dir=WR/('round11_tcp/results/run10/results/main' if is_tcp else 'round10_fpcache/results/main')
        gridfpdir=WR/('round11_tcp/results/grid10/results/grid' if is_tcp else 'round10_fpcache/results/grid')
        for kib in bs:
            bymode={}
            for mode in ('index','fp64'):
                suffix='-fp64' if mode=='fp64' else ''
                src=ROOT/'results/main'/mode
                baseline=read_rows(src,'BF+ReplayCache'+suffix,ds,kib)
                plain=read_rows(src,'BF'+suffix,ds,kib)
                ra=read_rows(r10dir if mode=='fp64' else r6dir,'RA6'+suffix,ds,kib)
                grid=read_rows(gridfpdir if mode=='fp64' else r5dir,'LearnGrid'+suffix,ds,kib)
                gama=read_rows(r5dir,'Gama',ds,kib)
                r4=read_rows(r5dir,'RA4',ds,kib)
                old_grid=read_rows(r5dir,'LearnGrid',ds,kib)
                assert len(baseline)==(1 if is_tcp else 75),(ds,kib,len(baseline))
                assert baseline.keys()==plain.keys()==ra.keys()==grid.keys()==gama.keys()==r4.keys()==old_grid.keys()
                bymode[mode]=baseline
                for key,b in baseline.items():
                    p=plain[key]
                    ref=r4[key]['fp_oracle']
                    ref=float(ref) if ref!='' else int(old_grid[key]['fp_tail'])
                    assert b['base_stream_sha256']==p['base_stream_sha256']
                    assert int(b['tail_len'])==int(p['tail_len'])
                    if key[0]!=PROBE:assert b['tail_stream_sha256']==p['tail_stream_sha256']
                    n=int(b['tail_len'])
                    row=dict(dataset=ds,budget_kib=kib,high_budget=kib==bs[-1],workload=key[0],seed=key[1],
                             cache=mode,is_tcp=is_tcp,group=group(key[0]),included=ref>=30,
                             reference_fp=ref,ra_fp=int(ra[key]['fp_tail']),replay_fp=int(grid[key]['fp_tail']),
                             gama_fp=int(gama[key]['fp_tail']),bf_fp=int(p['fp_tail']),bf_cache_fp=int(b['fp_tail']),
                             tail_len=n,selected_frac=float(b['frac']),used_bytes=int(b['total_bytes']),
                             cache_bytes=int(b['cache_alloc_bytes']),bf_k=int(b['k']),
                             ra_over_bf_cache=ratio(int(ra[key]['fp_tail']),int(b['fp_tail'])),
                             ra_fp_per_million=int(ra[key]['fp_tail'])/n*1e6,
                             bf_cache_fp_per_million=int(b['fp_tail'])/n*1e6)
                    rows.append(row)
            for key in bymode['index']:
                assert bymode['index'][key]['base_stream_sha256']==bymode['fp64'][key]['base_stream_sha256']
    assert len(rows)==1532
    with (ROOT/'results/row_comparisons.csv').open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    mainrows=[r for r in rows if not r['is_tcp'] and r['workload']!=PROBE]
    summary={}
    lines=['# 无模型 BF＋缓存强基线：完整预定结果', '',
           'RA6/Replay/Gama 为既有冻结结果，本轮只运行无模型 BF 和 BF＋缓存。BF 按一个实际 owning 数组计费，不扣不存在的模型和导航头。',
           '比值为 `(FP_RA6+1)/(FP_BFcache+1)`；小于 1 才是 RA6 更好。每条流前 25% 选配置、后 75% 测量，评估缓存冷启动。', '',
           '## COD、URL、Shalla：同格式缓存，逐案例比值', '',
           '| 缓存 | 数据/负载 | 纳入 | 排除低误报 | 中位 | 最差 | 胜/平/负 |',
           '|---|---|---:|---:|---:|---:|---|']
    for mode in ('index','fp64'):
        for label in (*BUDGETS,'1万','10万','全部','无重复','合计'):
            subset=[r for r in mainrows if r['cache']==mode and
                    (label=='合计' or r['dataset']==label or r['group']==label)]
            # '全部' is a pool label, not the aggregate; 合计 is all groups.
            selected=[r for r in subset if r['included']]
            st=summarize(selected)
            summary[f'{mode}/{label}']=dict(**st,excluded=len(subset)-len(selected))
            if selected:
                lines.append(f"| {mode} | {label} | {len(selected)} | {len(subset)-len(selected)} | "
                             f"{fmt_ratio(st['median'])} | {fmt_ratio(st['maximum'])} | {st['wins']}/{st['ties']}/{st['losses']} |")
    lines += ['', '筛选沿用第六轮的参照 FP≥30 规则，不按本轮谁赢筛选。完整未筛选行和每百万查询误报见 `row_comparisons.csv`。', '',
              '## 各设置的总误报（所有主负载，种子均值后按负载求和）', '',
              '| 缓存 | 数据 | KiB | 普通 BF | BF＋缓存 | RA6 | Replay | RA6/BF＋缓存 |',
              '|---|---|---:|---:|---:|---:|---:|---:|']
    for mode in ('index','fp64'):
        for ds,bs in BUDGETS.items():
            for kib in bs:
                subset=[r for r in mainrows if (r['cache'],r['dataset'],r['budget_kib'])==(mode,ds,kib)]
                grouped=defaultdict(list)
                for r in subset:grouped[r['workload']].append(r)
                total={c:sum(mean(r[c] for r in rs) for rs in grouped.values())
                       for c in ('bf_fp','bf_cache_fp','ra_fp','replay_fp')}
                lines.append(f"| {mode} | {ds} | {kib} | {total['bf_fp']:,.1f} | {total['bf_cache_fp']:,.1f} | "
                             f"{total['ra_fp']:,.1f} | {total['replay_fp']:,.1f} | {fmt_ratio(ratio(total['ra_fp'],total['bf_cache_fp']))} |")
    lines += ['', '## TCP-only：更准确的纯 BF 开销核验（不替换旧结果）', '',
              '| 缓存 | 数据 | KiB | BF＋缓存 | RA6 | 比值 |', '|---|---|---:|---:|---:|---:|']
    for r in rows:
        if r['is_tcp']:
            lines.append(f"| {r['cache']} | {r['dataset']} | {r['budget_kib']} | {r['bf_cache_fp']:,} | "
                         f"{r['ra_fp']:,} | {r['ra_over_bf_cache']:.3f} |")
    for mode in ('index','fp64'):
        st=summarize([r for r in rows if r['is_tcp'] and r['cache']==mode])
        summary[f'tcp/{mode}']=st
        lines.append(f"\n{mode}：中位 {st['median']:.3f}，胜/平/负 {st['wins']}/{st['ties']}/{st['losses']}。")
    lines += ['', '## 探测重放（单列，不是所有结构逐项相同的查询尾流）', '']
    for mode in ('index','fp64'):
        st=summarize([r for r in rows if r['workload']==PROBE and r['cache']==mode])
        summary[f'probe/{mode}']=st
        lines.append(f"- {mode}：{st['n']} 个案例，中位 {st['median']:.3f}、最大 {st['maximum']:.3f}，胜/平/负 {st['wins']}/{st['ties']}/{st['losses']}。")
    lines += ['', '## 统计边界', '',
              '- 模型、数据集、预算间的案例有依赖；此处不把数百行当作独立样本来宣称显著性。',
              '- 保存按数据集×负载组聚合的比值几何均值（`clusters.json`），用于核对收益集中在哪些数据/负载；只有三个合成数据集，不能泛化为普遍胜出。',
              '- BF＋缓存只回放 13 个缓存比例；RA6 同时搜索模型与分配。不能用本轮回放耗时宣称 RA6 比这个更简单的基线快。',
              '- 本轮 BF 效果差异包含模型判别和分段分配，以及选出的缓存大小，不是仅有“重复感知重新加权”的消融。',
              '- 更精确的 BF 物理表示与第十一轮保守扣除的头开销不同，且 k 按相邻整数比较；旧结果不覆盖写、不择优拼接。',
              '- 指纹版的理论与实测保证边界见 `deployment_audit.md`；完整构建成本见 `construction_cost.md`。']
    clusters=[]
    for mode in ('index','fp64'):
        groups=defaultdict(list)
        for r in mainrows:
            if r['cache']==mode and r['included']:groups[r['dataset'],r['group']].append(r)
        for (ds,g),rs in groups.items():
            clusters.append(dict(cache=mode,dataset=ds,workload_group=g,**summarize(rs)))
    (ROOT/'results/summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'results/clusters.json').write_text(json.dumps(clusters,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (ROOT/'results/report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    sources={}
    for r in ('round5_dp','round6_bucket','round10_fpcache','round11_tcp'):
        for p in (WR/r/'results').rglob('rows_*.csv'):
            sources[str(p.relative_to(WR))]=hashlib.sha256(p.read_bytes()).hexdigest()
    (ROOT/'results/reference_sources.json').write_text(json.dumps(sources,indent=2)+'\n')
    print('Report complete: 1532 cache-specific cases, 3064 measured BF/control rows.')


if __name__=='__main__':
    main()
