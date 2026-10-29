"""Original-code baselines vs round-3 methods on identical streams -> report.md, rows.json.

Static originals (Gama, PLBF) wrote per-test-key FP flags; their tail FP is evaluated here
on the same streams (first 25% learning, last 75% scored).  Stacked/AQF/SkiQF runners wrote
tail FP directly.  Round-3 rows come from windows_research/round3_ra_plbf/results/{main,high}.
Run with the project env.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
R3 = HERE.parent / 'windows_research' / 'round3_ra_plbf'
sys.path.insert(0, str(R3 / 'src'))
import ra_plbf as RA  # noqa: E402

E = RA.E
OURS = ('Gama', 'LearnGrid', 'StreamModel', 'RA-PLBF', 'RA-PLBF+G')
ORDER = ['cod', 'caida', 'shalla', 'url', 'caida_flow', 'mawi2021_flow', 'mawi2022_flow']
HIGH = {'cod': 4096, 'caida': 2048, 'shalla': 4096, 'caida_flow': 256, 'mawi2021_flow': 128, 'mawi2022_flow': 128}
TREES = json.loads((HERE / 'plbf' / 'gama_style_trees.json').read_text())


def static_sources(ds, kib):
    out = {}
    f = HERE / 'gama' / 'out' / ds / f'gama_{kib}.json'
    if f.exists():
        info = json.loads(f.read_text())
        out['Gama(original)'] = ('infeasible', info['infeasible']) if 'infeasible' in info else \
            (np.load(HERE / 'gama' / 'out' / ds / f'fp_{kib}.npy'), info)
    for t, label in ((48, 'PLBF(original,48树)'), (TREES.get(f'{ds}/{kib}'), 'PLBF(original,Gama式树数)')):
        f = HERE / 'plbf' / 'out' / ds / f't{t}' / f'plbf_{kib}.json'
        if t and f.exists():
            info = json.loads(f.read_text())
            out[label] = ('infeasible', info['infeasible']) if 'infeasible' in info else \
                (np.load(f.with_name(f'fp_{kib}.npy')), info)
    return out


def collect(ds, kib, setup, scores):
    rows = []
    tag = 'high' if HIGH.get(ds) == kib else 'main'
    f = R3 / 'results' / tag / ds / f'{kib}.json'
    if f.exists():
        rows += [dict(workload=r['workload'], seed=r['seed'], method=r['method'], fp_tail=r['fp_tail'])
                 for r in json.loads(f.read_text())['rows'] if r['method'] in OURS]
    notes = {}
    for sub, prefix in (('stacked', None), ('aqf', None), ('skiqf', None)):
        f = HERE / sub / 'out' / ds / f'{kib}.json'
        if not f.exists():
            continue
        for r in json.loads(f.read_text())['rows']:
            if r.get('infeasible') or r.get('error'):
                notes[r['method']] = 'infeasible' if r.get('infeasible') else 'error'
                continue
            rows.append(dict(workload=r['workload'], seed=r['seed'], method=r['method'], fp_tail=r['fp_tail'],
                             over_budget=r.get('over_budget', False),
                             actual_over_budget=(r.get('actual_bits', 0) / r['total_bits']) if 'total_bits' in r else None))
    statics = static_sources(ds, kib)
    for m, (flags, info) in statics.items():
        if isinstance(flags, str):
            notes[m] = 'infeasible'
    live = {m: v[0] for m, v in statics.items() if not isinstance(v[0], str)}
    if live:
        specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
        seeds = 1 if ds.endswith('_flow') else 5
        gama = min((c for c in (E.build(setup, scores, t, kib, 0.) for t in E.R.GAMA_TREES) if c),
                   key=lambda c: (c['structure'].est_fpr, c['trees']))
        for name, spec, family in specs:
            for seed in range(seeds):
                stream = E.stream_for(setup, name, spec, family, seed, 10_000_000, gama['structure'])
                tail = stream[len(stream) // 4:]
                for m, flags in live.items():
                    rows.append(dict(workload=name, seed=seed, method=m, fp_tail=int(flags[tail].sum())))
    return rows, notes


def table(all_rows, notes, skip=()):
    lines = []
    methods = ['RA-PLBF+G', 'RA-PLBF', 'LearnGrid', 'Gama', 'Gama(original)', 'PLBF(original,Gama式树数)',
               'PLBF(original,48树)', 'Stacked(original)', 'AdaptiveQF(original)', 'SkiQF(original)', 'HybridSkiQF(original)']
    lines.append('| 设置 | ' + ' | '.join(methods) + ' |')
    lines.append('|---|' + '---:|' * len(methods))
    for (ds, kib), rows in all_rows.items():
        acc = defaultdict(lambda: defaultdict(list))
        for r in rows:
            if r['workload'] not in skip:
                acc[r['method']][r['workload']].append(r['fp_tail'])
        tot = {m: sum(np.mean(v) for v in w.values()) for m, w in acc.items()}
        nw = len(acc.get('RA-PLBF+G', {}))
        cells = []
        for m in methods:
            if m in tot and len(acc[m]) == nw:
                cells.append(f'{tot[m]:,.0f}')
            elif notes[(ds, kib)].get(m) == 'infeasible':
                cells.append('放不下')
            elif m in tot:
                cells.append(f'{tot[m]:,.0f}（{len(acc[m])}/{nw}）')
            else:
                cells.append('—')
        star = ' ★' if HIGH.get(ds) == kib else ''
        lines.append(f'| {ds} {kib}{star} | ' + ' | '.join(cells) + ' |')
    return lines


PROBE = '探测重放10%'
NOTE_PROBE = ('"探测重放"负载按第二轮协议，重放的是 Gama（我们的 Gama 式结构）自己被观察到的误报 key，'
              '所以它只对 Gama 这一行构成定向攻击（约为尾段查询的 10%），对其他方法不对称。下表去掉这个负载。')


def write(all_rows, notes):
    lines = ['# 原版代码基线与方法 C 的对比（尾段误报总数）', '',
             '对种子取均值再对负载求和（真实轨迹为一次运行）。"放不下"表示原版在该预算下无法构造；'
             '括号表示只完成了部分负载。★ 为每 key ≥8 bit 的高预算点。', '', '## 全部负载', ''] + table(all_rows, notes)
    lines += ['', '## 去掉探测重放负载', '', NOTE_PROBE, ''] + table(all_rows, notes, skip=(PROBE,))
    (HERE / 'report.md').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines))


def main():
    if '--from-rows' in sys.argv:
        raw = json.loads((HERE / 'rows.json').read_text())
        all_rows = {(k.split('/')[0], int(k.split('/')[1])): v for k, v in raw.items()}
        notes = json.loads((HERE / 'notes.json').read_text()) if (HERE / 'notes.json').exists() else {}
        notes = defaultdict(dict, {(k.split('/')[0], int(k.split('/')[1])): v for k, v in notes.items()})
        return write(all_rows, notes)
    budgets = {ds: list(E.BUDGETS[ds]) + ([HIGH[ds]] if ds in HIGH else []) for ds in ORDER}
    all_rows, notes = {}, {}
    for ds in ORDER:
        setup, scores, _ = E.load(ds)
        for kib in budgets[ds]:
            all_rows[ds, kib], notes[ds, kib] = collect(ds, kib, setup, scores)
            print(ds, kib, len(all_rows[ds, kib]), notes[ds, kib], flush=True)
        E.R._GSETUPS.clear()
    (HERE / 'rows.json').write_text(json.dumps({f'{d}/{k}': v for (d, k), v in all_rows.items()}, ensure_ascii=False))
    (HERE / 'notes.json').write_text(json.dumps({f'{d}/{k}': v for (d, k), v in notes.items()}, ensure_ascii=False))
    write(all_rows, notes)


if __name__ == '__main__':
    main()
