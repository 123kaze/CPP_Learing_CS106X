"""Round-5 report: E1 main table + pass criteria, E2 regret, E3 prediction accuracy, E6 ablations.

Reads results/rows_*.csv and results/e3_*.jsonl; writes results/report.md, results/all_rows.csv
and figures/e2_regret.png, figures/e3_pred_vs_measured.png.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]
RES = ROOT / 'results'
FIG = ROOT / 'figures'
ORDER = ['cod', 'caida', 'shalla', 'url', 'caida_flow', 'mawi2020_flow', 'mawi2021_flow', 'mawi2022_flow']
HIGH = {'cod': 4096, 'caida': 2048, 'shalla': 4096, 'caida_flow': 256, 'mawi2020_flow': 128,
        'mawi2021_flow': 128, 'mawi2022_flow': 128}
MAIN = ['FastPLBF48', 'Gama', 'Gama(original)', 'Gama+10%', 'LearnGrid', 'RA4']
ABL = ['RA4-noRepeat', 'RA4-noSA', 'RA4-noGT', 'RA4-mix0.5', 'RA4-mix1', 'RA4-Table', 'RA-global']
NOREP = ('每key一次', '全新对抗')


def ratio(a, b):
    return (a + 1) / (b + 1)


def load_rows():
    rows = []
    for f in sorted(RES.glob('rows_*.csv')):
        with f.open(encoding='utf-8') as fh:
            rows += list(csv.DictReader(fh))
    for r in rows:
        r['budget_kib'] = int(r['budget_kib'])
        r['seed'] = int(r['seed'])
        r['fp_tail'] = int(r['fp_tail'])
        assert int(r['total_bytes']) <= r['budget_kib'] * 1024
    return rows


def label(ds, kib):
    return f"{ds} {kib}{' ★' if HIGH.get(ds) == kib else ''}"


def by_setting(rows):
    out = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))   # (ds,kib) -> workload -> seed -> method -> row
    for r in rows:
        out[r['dataset'], r['budget_kib']][r['workload']][r['seed']][r['method']] = r
    return dict(sorted(out.items(), key=lambda kv: (ORDER.index(kv[0][0]), kv[0][1])))


def wmean(ws, method, seeds=None):
    """Seed-mean tail FP per workload (only workloads/seeds where the method exists)."""
    out = {}
    for w, ss in ws.items():
        v = [ss[s][method]['fp_tail'] for s in ss if method in ss[s] and (seeds is None or s in seeds)]
        if v:
            out[w] = float(np.mean(v))
    return out


def e1(S, L):
    L += ['## E1 主表（DP 分配器，按设置的尾段误报总量，种子均值后对负载求和）', '',
          '| 设置 | 负载 | FastPLBF48 | Gama | Gama 原版 | Gama+10% | 网格 | **RA4** | RA4/Gama | RA4/网格 | RA4/事后最优 | RA4 树数 / 缓存KB |',
          '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    crit = dict(n=0, gama1pct=0, norep_total=0, norep_equal=0, grid_med=[], per_wl=[])
    for (ds, kib), ws in S.items():
        tot = {m: sum(wmean(ws, m).values()) for m in MAIN}
        nw = {m: len(wmean(ws, m)) for m in MAIN}
        orc = {w: np.mean([float(ss[s]['RA4']['fp_oracle']) for s in ss if s < 3 and ss[s]['RA4']['fp_oracle'] != ''])
               for w, ss in ws.items() if any(s < 3 for s in ss)}
        ra_s012 = wmean(ws, 'RA4', seeds={0, 1, 2})
        ra_or = ratio(sum(ra_s012[w] for w in orc), sum(orc.values())) if orc else float('nan')
        ra_rows = [ss[s]['RA4'] for ss in ws.values() for s in ss]
        trees = sorted({int(r['trees']) for r in ra_rows})
        cache = np.median([int(r['cache_alloc_bytes']) / 1024 for r in ra_rows])
        cell = lambda m: (f'{tot[m]:,.0f}' if nw[m] == len(ws) else (f'{tot[m]:,.0f}（{nw[m]}/{len(ws)}）' if nw[m] else '—'))  # noqa: E731
        L.append(f"| {label(ds, kib)} | {len(ws)} | {cell('FastPLBF48')} | {cell('Gama')} | {cell('Gama(original)')} | "
                 f"{cell('Gama+10%')} | {cell('LearnGrid')} | **{cell('RA4')}** | {ratio(tot['RA4'], tot['Gama']):.3f} | "
                 f"{ratio(tot['RA4'], tot['LearnGrid']):.3f} | {ra_or:.3f} | {trees} / {cache:.1f} |")
        crit['n'] += 1
        crit['gama1pct'] += tot['RA4'] <= 1.01 * tot['Gama']
        ra, ga, gr = wmean(ws, 'RA4'), wmean(ws, 'Gama'), wmean(ws, 'LearnGrid')
        for w in ws:
            crit['per_wl'].append(ratio(ra[w], gr[w]))
            if w in NOREP:
                crit['norep_total'] += 1
                crit['norep_equal'] += all(ss['RA4']['fp_tail'] == ss['Gama']['fp_tail'] for ss in ws[w].values())
        crit['grid_med'].append(np.median([ratio(ra[w], gr[w]) for w in ws]))
    pw = np.array(crit['per_wl'])
    L += ['', '**过关标准**', '',
          f"- 按总量 RA4 不比 Gama 差超过 1%：{crit['gama1pct']}/{crit['n']} 个设置。",
          f"- 无重复负载上与 Gama 逐位一致：{crit['norep_equal']}/{crit['norep_total']} 个（设置×负载，所有种子）。",
          f"- 对网格的逐负载比值：中位数 {np.median(pw):.3f}（{len(pw)} 个），≤1 的占 {np.mean(pw <= 1):.0%}，"
          f"最坏 {pw.max():.3f}；各设置中位数 ≤1 的设置 {sum(m <= 1 for m in crit['grid_med'])}/{crit['n']}。", '']
    return crit


def e2(S, L):
    reg = defaultdict(list)
    for (ds, kib), ws in S.items():
        for w, ss in ws.items():
            for s, ms in ss.items():
                if s >= 3 or ms['RA4']['fp_oracle'] == '':
                    continue
                o = float(ms['RA4']['fp_oracle'])
                for m in ('RA4', 'LearnGrid', 'Gama', 'Gama+10%', 'RA-global'):
                    if m in ms:
                        reg[m].append((ms[m]['fp_tail'] - o) / max(o, 1))
    L += ['## E2 与事后最优的差距（种子 0–2；遗憾值 =(fp−fp_最优)/max(fp_最优,1)）', '',
          '事后最优 = 网格候选集（Gama 分配 × 缓存比例）在评估段上的最少者。RA4 的分段加权不在这个候选集里，所以可以低于它（遗憾值为负）。', '',
          '| 方法 | 案例 | 中位遗憾 | 90 分位 | 最大 | 低于事后最优的比例 |', '|---|---:|---:|---:|---:|---:|']
    for m, v in reg.items():
        v = np.array(v)
        L.append(f'| {m} | {len(v)} | {np.median(v):.3f} | {np.quantile(v, .9):.3f} | {v.max():.2f} | {np.mean(v < 0):.0%} |')
    L.append('')
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        FIG.mkdir(exist_ok=True)
        fig, ax = plt.subplots(figsize=(6, 3.2))
        names = list(reg)
        ax.boxplot([np.clip(reg[m], -1, 10) for m in names], showfliers=True)
        ax.set_xticks(range(1, len(names) + 1), names)
        ax.set_ylabel('regret vs hindsight (clipped to [-1, 10])')
        ax.axhline(0, color='gray', lw=.5)
        fig.tight_layout()
        fig.savefig(FIG / 'e2_regret.png', dpi=160)
        plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        L.append(f'（遗憾值图未生成：{exc}）')


def e3(L):
    preds = ('pred', 'pred_noSA', 'pred_noGT', 'pred_mix0.5')
    stats = {p: dict(rho=[], rel=[], top1=[], top3=[]) for p in preds}
    pts = []
    n = 0
    for f in sorted(RES.glob('e3_*.jsonl')):
        for line in f.read_text(encoding='utf-8').splitlines():
            rec = json.loads(line)
            cs = rec['candidates']
            if len(cs) < 3:
                continue
            n += 1
            meas = np.array([c['measured'] for c in cs], float)
            best = meas.min()
            for p in preds:
                if p not in cs[0]:
                    continue
                pr = np.array([c[p] for c in cs], float)
                if np.ptp(pr) > 0 and np.ptp(meas) > 0:
                    stats[p]['rho'].append(spearmanr(pr, meas).statistic)
                ok = meas > 0
                stats[p]['rel'] += list(np.abs(pr[ok] - meas[ok]) / meas[ok])
                order = np.argsort(pr, kind='stable')
                stats[p]['top1'].append(meas[order[0]] == best)
                stats[p]['top3'].append(best in meas[order[:3]])
                if p == 'pred':
                    pts += list(zip(pr, meas))
    L += [f'## E3 预测准确度（种子 0，{n} 个设置×负载，每个都是 RA4 的全部候选：各自建好、在评估段实测）', '',
          '同一批候选结构，用不同预测器给出预测值：完整 RA4、去掉组相联修正、关 Good–Turing、NEW_MIX=0.5。', '',
          '| 预测器 | Spearman 中位数 | 相对误差中位数 | 相对误差 90 分位 | top-1 命中 | top-3 命中 |', '|---|---:|---:|---:|---:|---:|']
    for p, s in stats.items():
        if s['top1']:
            L.append(f"| {p} | {np.median(s['rho']):.3f} | {np.median(s['rel']):.3f} | {np.quantile(s['rel'], .9):.3f} | "
                     f"{np.mean(s['top1']):.0%} | {np.mean(s['top3']):.0%} |")
    L += ['', '过关建议：Spearman 中位数 ≥ 0.9，top-3 命中 ≥ 80%。分段一级的偏差这一轮没有记录（见结论里的待办）。', '']
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        if pts:
            a = np.array(pts) + 1
            fig, ax = plt.subplots(figsize=(4.2, 4))
            ax.loglog(a[:, 1], a[:, 0], '.', ms=2, alpha=.4)
            lim = [a.min(), a.max()]
            ax.plot(lim, lim, 'k-', lw=.6)
            ax.set_xlabel('measured tail FP + 1')
            ax.set_ylabel('RA4 predicted tail FP + 1')
            fig.tight_layout()
            fig.savefig(FIG / 'e3_pred_vs_measured.png', dpi=160)
            plt.close(fig)
    except Exception as exc:  # noqa: BLE001
        L.append(f'（散点图未生成：{exc}）')


def e6(S, L):
    L += ['## E6 消融（种子 0–2；对完整 RA4 的逐负载比值）', '',
          '| 变体 | 中位数 | 最坏 | 真实轨迹中位数 | 比 RA4 好的比例 |', '|---|---:|---:|---:|---:|']
    for m in ABL:
        rs, real = [], []
        for (ds, kib), ws in S.items():
            a, b = wmean(ws, m, {0, 1, 2}), wmean(ws, 'RA4', {0, 1, 2})
            for w in a:
                rs.append(ratio(a[w], b[w]))
                if ds.endswith('_flow'):
                    real.append(rs[-1])
        if rs:
            rs = np.array(rs)
            L.append(f'| {m} | {np.median(rs):.3f} | {rs.max():.2f} | {np.median(real) if real else float("nan"):.3f} | {np.mean(rs < 1):.0%} |')
    L.append('')


def misc(rows, L):
    u = [int(r['cache_alloc_bytes']) / int(r['cache_reserved_bytes']) for r in rows if int(r['cache_reserved_bytes']) >= 4096]
    small = [int(r['cache_alloc_bytes']) / int(r['cache_reserved_bytes']) for r in rows if 0 < int(r['cache_reserved_bytes']) < 4096]
    L += ['## 记账与缓存利用率', '',
          f'- 所有 {len(rows)} 行都满足 total_bytes ≤ 预算（读入时逐行断言）；零假阴性由构建时的断言保证。',
          f'- 缓存实际分配/预留：预留 ≥4KB 的 {len(u)} 行，最小 {min(u) if u else float("nan"):.4f}，中位 {np.median(u) if u else float("nan"):.4f}；'
          f'预留 <4KB 的 {len(small)} 行，最小 {min(small) if small else float("nan"):.4f}（固定数组头占比大，未分配字节返还 BF）。', '']


def main():
    rows = load_rows()
    S = by_setting(rows)
    L = ['# 第五轮结果（FastPLBF DP 分配器 + 任意桶数缓存 + 对称探测重放）', '']
    e1(S, L)
    e2(S, L)
    e3(L)
    e6(S, L)
    misc(rows, L)
    (RES / 'report.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    with (RES / 'all_rows.csv').open('w', encoding='utf-8', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print('\n'.join(L))


if __name__ == '__main__':
    main()
