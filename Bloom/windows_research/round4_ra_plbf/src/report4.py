"""Round-4 report: RA4 variants vs the round-3 baselines on identical streams.

usage: report4.py [--tag main|high|holdout]  (holdout reads round-3 rows from results/holdout too)
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
R3 = ROOT.parent / 'round3_ra_plbf' / 'results'
ORDER = ['cod', 'caida', 'shalla', 'url', 'caida_flow', 'mawi2021_flow', 'mawi2022_flow', 'mawi2023_flow']
BASE = ('Gama', 'StreamModel', 'LearnGrid', 'Fixed48Grid', 'RA-PLBF')   # RA-PLBF = round 3 (NEW_MIX 0.5)
VAR = ('RA4', 'RA4+G', 'RA4-mix0.5', 'RA4-mix1', 'RA4-noSA', 'RA4-noGT', 'RA4-noRepeat', 'RA4-Table')


def ratio(a, b):
    return (a + 1) / (b + 1)


def load(tags):
    data = {}
    for tag in tags:
        for f in sorted((ROOT / 'results' / tag).glob('*/*.json')):
            ds, kib = f.parent.name, int(f.stem)
            d4 = json.loads(f.read_text(encoding='utf-8'))
            d3 = json.loads((R3 / tag / ds / f'{kib}.json').read_text(encoding='utf-8'))
            rows = [r for r in d3['rows'] if r['method'] in BASE] + d4['rows']
            data[ds, kib, tag] = dict(rows=rows, sel=d4['selections'], completed=d4['completed'],
                                      r3rows=d3['rows'])
    return dict(sorted(data.items(), key=lambda kv: (kv[0][2] != 'main', ORDER.index(kv[0][0]), kv[0][1])))


def means(rows):
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        acc[r['workload']][r['method']].append(r['fp_tail'])
    return {w: {m: float(np.mean(v)) for m, v in d.items()} for w, d in acc.items()}


def label(ds, kib, tag):
    return f"{ds} {kib}{' ★' if tag == 'high' else ''}"


def main(tags):
    data = load(tags)
    L = [f"# 第四轮结果（{'、'.join(tags)}）", '',
         '基线和第三轮 RA-PLBF（NEW_MIX=0.5）取自第三轮在相同流上的结果。比值 (方法+1)/(网格+1) 先对种子取均值；'
         '总量为各负载均值之和。★ 为高预算点。', '']
    L += ['## C2：按设置的尾段误报总量', '',
          '| 设置 | 完成 | Gama | 网格 | 误报流模型 | 第三轮 RA | **RA4** | RA4+G | RA4/网格 | RA4/Gama |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    allr = defaultdict(list)
    crit = dict(grid_median=0, grid_total=0, gama_all=0, gama_total=0, n=0)
    worst_gama = []
    for (ds, kib, tag), d in data.items():
        mw = means(d['rows'])
        mw = {w: x for w, x in mw.items() if 'RA4' in x}
        tot = {m: sum(x[m] for x in mw.values() if m in x) for m in BASE + VAR}
        L.append(f"| {label(ds, kib, tag)} | {'是' if d['completed'] else f'{len(mw)} 负载'} | {tot['Gama']:,.0f} | {tot['LearnGrid']:,.0f} | "
                 f"{tot['StreamModel']:,.0f} | {tot['RA-PLBF']:,.0f} | **{tot['RA4']:,.0f}** | {tot['RA4+G']:,.0f} | "
                 f"{ratio(tot['RA4'], tot['LearnGrid']):.3f} | {ratio(tot['RA4'], tot['Gama']):.3f} |")
        for m in VAR + ('RA-PLBF', 'StreamModel'):
            allr[m] += [ratio(x[m], x['LearnGrid']) for x in mw.values() if m in x]
        crit['n'] += 1
        crit['grid_median'] += np.median([ratio(x['RA4'], x['LearnGrid']) for x in mw.values()]) <= 1
        crit['grid_total'] += tot['RA4'] <= tot['LearnGrid']
        crit['gama_all'] += all(x['RA4'] <= x['Gama'] for x in mw.values())
        crit['gama_total'] += tot['RA4'] <= tot['Gama']
        for w, x in mw.items():
            if x['RA4'] > x['Gama']:
                worst_gama.append((ratio(x['RA4'], x['Gama']), label(ds, kib, tag), w, x['Gama'], x['RA4']))
    L += ['', '逐负载对网格的比值（全部设置×负载）：', '',
          '| 方法 | 个数 | 中位数 | ≤1 的比例 | >1.1 的比例 | 最坏 |', '|---|---:|---:|---:|---:|---:|']
    for m in ('RA4', 'RA4+G', 'RA-PLBF', 'StreamModel') + VAR[2:]:
        rs = np.array(allr[m])
        if len(rs):
            L.append(f'| {m} | {len(rs)} | {np.median(rs):.3f} | {np.mean(rs <= 1):.0%} | {np.mean(rs > 1.1):.0%} | {rs.max():.3f} |')

    L += ['', '## C5 判据（主方法 RA4，不靠护栏）', '',
          f"- 不比网格差：按负载比值中位数 {crit['grid_median']}/{crit['n']} 个设置；按总量 {crit['grid_total']}/{crit['n']}。",
          f"- 不比 Gama 差：按总量 {crit['gama_total']}/{crit['n']}；逐负载每个都不多于 Gama 的设置 {crit['gama_all']}/{crit['n']}。",
          f'- RA4 多于 Gama 的负载共 {len(worst_gama)} 个，最大的几个：', '']
    for r, lab, w, g, a in sorted(worst_gama, reverse=True)[:10]:
        L.append(f'  - {lab} {w}：Gama {g:,.1f}，RA4 {a:,.1f}（{r:.3f}×）')

    L += ['', '## 退化检查：无重复负载上 RA4 与 Gama', '',
          '| 设置 | 负载 | Gama | RA4 | 第三轮 RA（0.5） |', '|---|---|---:|---:|---:|']
    for (ds, kib, tag), d in data.items():
        for w, x in means(d['rows']).items():
            if w in ('每key一次', '全新对抗') and 'RA4' in x:
                L.append(f"| {label(ds, kib, tag)} | {w} | {x['Gama']:,.1f} | {x['RA4']:,.1f} | {x['RA-PLBF']:,.1f} |")

    L += ['', '## 敏感性与消融（对 RA4 的逐负载比值，中位/最坏）', '',
          '| 设置 | NEW_MIX=0.5 | NEW_MIX=1 | 关组相联 | 关 Good–Turing | 重复折扣 0 | 表格原式 |', '|---|---:|---:|---:|---:|---:|---:|']
    for (ds, kib, tag), d in data.items():
        mw = means(d['rows'])
        cells = []
        for m in VAR[2:]:
            rs = [ratio(x[m], x['RA4']) for x in mw.values() if m in x and 'RA4' in x]
            cells.append(f'{np.median(rs):.3f} / {max(rs):.3f}' if rs else '—')
        L.append(f'| {label(ds, kib, tag)} | ' + ' | '.join(cells) + ' |')

    L += ['', '## C3：预测与实测（RA4 的部署配置）', '',
          '"有修正"/"无修正"是同一部署配置下，带或不带组相联修正的预测误报总数；比值为预测/实测，取中位数，并给出落在 2 倍以内的比例。', '',
          '| 设置 | 案例 | 有修正 中位 | 有修正 2 倍内 | 无修正 中位 | 无修正 2 倍内 | 段级 2 倍内（有修正，按误报加权） |',
          '|---|---:|---:|---:|---:|---:|---:|']
    for (ds, kib, tag), d in data.items():
        a, b, ok, wsum = [], [], 0., 0.
        for s in d['sel']:
            i = s['ra'].get('RA4')
            if i is None:
                continue
            meas = np.array(i['seg_measured'])
            pred = np.array(i['seg_predicted'])
            a.append((i['predicted_fp_setassoc'] + 1) / (meas.sum() + 1))
            b.append((i['predicted_fp_fullassoc'] + 1) / (meas.sum() + 1))
            big = (pred >= 20) | (meas >= 20)
            good = big & (np.abs(np.log((pred + 1) / (meas + 1))) <= np.log(2))
            ok += meas[good].sum()
            wsum += meas[big].sum()
        if a:
            a, b = np.array(a), np.array(b)
            w2 = lambda v: np.mean(np.abs(np.log(v)) <= np.log(2))  # noqa: E731
            L.append(f'| {label(ds, kib, tag)} | {len(a)} | {np.median(a):.3f} | {w2(a):.0%} | {np.median(b):.3f} | {w2(b):.0%} | {ok / max(wsum, 1):.0%} |')

    L += ['', '## 学习期内存与选择时间（中位数）', '',
          '| 设置 | RA4 学习期状态 MB | 网格回放轨迹 MB | RA4 选择 s | 网格回放 s | 误报流模型 s |', '|---|---:|---:|---:|---:|---:|']
    for (ds, kib, tag), d in data.items():
        sec, mem = defaultdict(list), defaultdict(list)
        for r in d['rows']:
            sec[r['method']].append(r['selection_seconds'])
        for r in d['r3rows']:
            if r['method'] == 'LearnGrid':
                mem['grid'].append(r['learning_trace_bytes'] / 1e6)
        for r in d['rows']:
            if r['method'] == 'RA4':
                mem['ra'].append(r['learning_state_bytes'] / 1e6)
        L.append(f"| {label(ds, kib, tag)} | {np.median(mem['ra']):.1f} | {np.median(mem['grid']):.1f} | "
                 f"{np.median(sec['RA4']):.2f} | {np.median(sec['LearnGrid']):.2f} | {np.median(sec['StreamModel']):.2f} |")
    name = '_'.join(tags)
    (ROOT / 'results' / f'report_{name}.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tags', default='main,high')
    main(p.parse_args().tags.split(','))
