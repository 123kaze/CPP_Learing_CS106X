"""C2-C5 summary from results/<tag>/<dataset>/<kib>.json -> report.md, summary.json."""
import argparse
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
ROUND2 = ROOT.parent / 'round2_backlog' / 'results' / 'main'
METHODS = ['Gama', 'StreamModel', 'LearnGrid', 'Fixed48Grid', 'RA-PLBF', 'RA-PLBF+G',
           'RA-Zipf', 'RA-NoRepeat', 'RA-GlobalCache']
ORDER = ['cod', 'caida', 'shalla', 'url', 'caida_flow', 'mawi2021_flow', 'mawi2022_flow']


def load(tag):
    out = {}
    for f in sorted((ROOT / 'results' / tag).glob('*/*.json')):
        d = json.loads(f.read_text(encoding='utf-8'))
        out[f.parent.name, int(f.stem)] = d
    return dict(sorted(out.items(), key=lambda kv: (ORDER.index(kv[0][0]) if kv[0][0] in ORDER else 99, kv[0][1])))


def means(rows):
    """{workload: {method: mean tail FP over seeds}} plus seed counts."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        acc[r['workload']][r['method']].append(r['fp_tail'])
    return {w: {m: float(np.mean(v)) for m, v in d.items()} for w, d in acc.items()}


def ratio(a, b):
    return (a + 1) / (b + 1)


def wtl(mw, m, ref):
    w = t = l = 0
    for d in mw.values():
        if m in d and ref in d:
            if d[m] < d[ref]:
                w += 1
            elif d[m] == d[ref]:
                t += 1
            else:
                l += 1
    return w, t, l


def round2_check(ds, kib, rows):
    """Exact agreement of shared baselines with the Windows round-2 rows."""
    f = ROUND2 / ds / f'{kib}.json'
    if not f.exists():
        return None
    old = {(r['workload'], r['seed'], r['method']): r['fp_tail'] for r in json.loads(f.read_text(encoding='utf-8'))['rows']}
    same = diff = 0
    for r in rows:
        k = (r['workload'], r['seed'], r['method'])
        if r['method'] in ('Gama', 'StreamModel', 'LearnGrid', 'Fixed48Grid') and k in old:
            same += old[k] == r['fp_tail']
            diff += old[k] != r['fp_tail']
    return same, diff


def main(tag):
    data = load(tag)
    lines = [f'# 方法 C（RA-PLBF）结果：`results/{tag}`', '']
    summary = dict(settings=[])
    lines += ['## C2 主对比：各方法对学习期网格回放（LearnGrid）', '',
              '先对种子取尾段误报均值，再算 (方法+1)/(网格+1)。小于 1 表示比网格好。胜/平/负按负载计。', '',
              '| 数据集 | KiB | 负载数 | 完成 | RA-PLBF 中位/最坏 | RA-PLBF 胜/平/负 | RA-PLBF+G 中位/最坏 | +G 胜/平/负 | 误报流模型 中位/最坏 | +G 对 Gama 最坏 | 与第二轮一致 |',
              '|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---|']
    all_ratio = defaultdict(list)
    for (ds, kib), d in data.items():
        mw = means(d['rows'])
        st = dict(dataset=ds, kib=kib, workloads=len(mw), completed=d['completed'])
        cells = []
        for m in ('RA-PLBF', 'RA-PLBF+G', 'StreamModel'):
            rs = [ratio(x[m], x['LearnGrid']) for x in mw.values() if m in x and 'LearnGrid' in x]
            all_ratio[m] += rs
            st[m] = dict(median=float(np.median(rs)), worst=float(max(rs)), wtl=wtl(mw, m, 'LearnGrid'))
            cells.append(f"{np.median(rs):.3f} / {max(rs):.3f}")
            if m != 'StreamModel':
                cells.append('/'.join(map(str, wtl(mw, m, 'LearnGrid'))))
        g = [ratio(x['RA-PLBF+G'], x['Gama']) for x in mw.values() if 'RA-PLBF+G' in x]
        st['guard_vs_gama_worst'] = float(max(g))
        chk = round2_check(ds, kib, d['rows'])
        st['round2_same_diff'] = chk
        lines.append(f"| {ds} | {kib} | {len(mw)} | {'是' if d['completed'] else '进行中'} | {cells[0]} | {cells[1]} | {cells[2]} | {cells[3]} | {cells[4]} | {max(g):.3f} | "
                     + ('—' if chk is None else f'{chk[0]} 行相同，{chk[1]} 行不同') + ' |')
        summary['settings'].append(st)
    lines += ['']
    for m, rs in all_ratio.items():
        rs = np.array(rs)
        lines.append(f'- {m}：全部 {len(rs)} 个（设置×负载）对网格，中位数 {np.median(rs):.3f}，'
                     f'≤1 的占 {np.mean(rs <= 1):.0%}，>1.1 的占 {np.mean(rs > 1.1):.0%}，最坏 {rs.max():.3f}。')

    lines += ['', '## C5 判据', '',
              '"不比网格差"：该设置下 RA 的负载级比值中位数 ≤ 1；"不比 Gama 差"：该设置每个负载都满足 (RA+1)/(Gama+1) ≤ 1。', '',
              '| 方法 | 不比网格差的设置 | 每个负载都不比 Gama 差的设置 |', '|---|---:|---:|']
    for m in ('RA-PLBF', 'RA-PLBF+G'):
        a = b = 0
        for (ds, kib), d in data.items():
            mw = means(d['rows'])
            a += np.median([ratio(x[m], x['LearnGrid']) for x in mw.values() if m in x]) <= 1
            b += all(ratio(x[m], x['Gama']) <= 1 for x in mw.values() if m in x)
        lines.append(f'| {m} | {a}/{len(data)} | {b}/{len(data)} |')

    lines += ['', '## 逐负载最坏的情况（RA-PLBF+G 对网格）', '',
              '| 数据集 | KiB | 负载 | 网格 | RA-PLBF | RA-PLBF+G | Gama | 误报流模型 |', '|---|---:|---|---:|---:|---:|---:|---:|']
    worst = []
    for (ds, kib), d in data.items():
        for w, x in means(d['rows']).items():
            if 'RA-PLBF+G' in x:
                worst.append((ratio(x['RA-PLBF+G'], x['LearnGrid']), ds, kib, w, x))
    for r, ds, kib, w, x in sorted(worst, key=lambda z: -z[0])[:12]:
        lines.append(f"| {ds} | {kib} | {w} | {x['LearnGrid']:.0f} | {x['RA-PLBF']:.0f} | {x['RA-PLBF+G']:.0f} | {x['Gama']:.0f} | {x['StreamModel']:.0f} |")

    lines += ['', '## C3 估计准确度（RA-PLBF 的部署配置）', '',
              '每个（设置×负载×种子）：预测的尾段误报总数对实测；每段：只计实测或预测 ≥20 次的段。', '',
              '| 数据集 | KiB | 案例 | 总量 预测/实测 中位 | 总量在 2 倍内 | 段级在 2 倍内（按误报加权） | 护栏保留 RA 的比例 |', '|---|---:|---:|---:|---:|---:|---:|']
    for (ds, kib), d in data.items():
        tot, seg_ok, seg_w, kept = [], 0., 0., []
        for s in d['selections']:
            i = s['ra'].get('RA-PLBF')
            if i is None:
                continue
            pred, meas = np.array(i['seg_predicted']), np.array(i['seg_measured'])
            tot.append((pred.sum() + 1) / (meas.sum() + 1))
            big = (pred >= 20) | (meas >= 20)
            ok = big & (np.abs(np.log((pred + 1) / (meas + 1))) <= np.log(2))
            seg_ok += meas[ok].sum()
            seg_w += meas[big].sum()
            kept.append(s['guard']['kept_ra'])
        if tot:
            tot = np.array(tot)
            lines.append(f"| {ds} | {kib} | {len(tot)} | {np.median(tot):.3f} | {np.mean(np.abs(np.log(tot)) <= np.log(2)):.0%} | "
                         f"{seg_ok / max(seg_w, 1):.0%} | {np.mean(kept):.0%} |")

    lines += ['', '## C4 消融：各变体对 RA-PLBF', '',
              '| 数据集 | KiB | RA-Zipf 中位/最坏 | RA-NoRepeat 中位/最坏 | RA-GlobalCache 中位/最坏 |', '|---|---:|---:|---:|---:|']
    for (ds, kib), d in data.items():
        mw = means(d['rows'])
        cells = []
        for m in ('RA-Zipf', 'RA-NoRepeat', 'RA-GlobalCache'):
            rs = [ratio(x[m], x['RA-PLBF']) for x in mw.values() if m in x and 'RA-PLBF' in x]
            cells.append(f'{np.median(rs):.3f} / {max(rs):.3f}' if rs else '—')
        lines.append(f'| {ds} | {kib} | ' + ' | '.join(cells) + ' |')

    lines += ['', '## 选择开销（秒，中位数）', '', '| 数据集 | KiB | 误报流模型 | 网格回放 | RA-PLBF | RA-PLBF+G | RA 学习期状态 MB |', '|---|---:|---:|---:|---:|---:|---:|']
    for (ds, kib), d in data.items():
        sec = defaultdict(list)
        mb = []
        for r in d['rows']:
            sec[r['method']].append(r['selection_seconds'])
            if r['method'] == 'RA-PLBF':
                mb.append(r['learning_state_bytes'] / 1e6)
        lines.append(f"| {ds} | {kib} | " + ' | '.join(f"{np.median(sec[m]):.2f}" for m in ('StreamModel', 'LearnGrid', 'RA-PLBF', 'RA-PLBF+G'))
                     + f' | {np.median(mb):.1f} |')
    (ROOT / 'results' / tag / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    (ROOT / 'results' / tag / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print('\n'.join(lines))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--tag', default='main')
    main(p.parse_args().tag)
