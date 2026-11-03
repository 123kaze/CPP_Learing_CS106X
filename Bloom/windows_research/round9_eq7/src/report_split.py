"""results/split_*.json -> results/bias_split.md  (where RA6's over-prediction comes from)

Groups and the MIN_REF split as report.py.  All columns are sums over the cases of a group, for
RA6's pick in each case: predicted vs measured tail misses, split into keys seen / not seen in the
learning period, and for the unseen keys the measured tail FP queries (no-cache misses) and distinct
FP keys (lower bound with a cache).
"""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from report import grp, ORDER, MIN_REF

ROOT = Path(__file__).resolve().parents[1]
F = ('pred_total', 'meas_total', 'pred_seen', 'meas_seen', 'pred_new', 'new_q_fp', 'new_d_fp', 'meas_new',
     'G_total', 'new_q', 'new_d')


def line(name, xs):
    """Per case: relative error (pred - meas) / meas and its two additive parts; medians.
    Then sums over the group for the unseen-key mechanism columns."""
    xs_ok = [x for x in xs if x['meas_total'] > 0]
    e = np.array([(x['pred_total'] - x['meas_total']) / x['meas_total'] for x in xs_ok])
    en = np.array([(x['pred_new'] - x['meas_new']) / x['meas_total'] for x in xs_ok])
    es = np.array([(x['pred_seen'] - x['meas_seen']) / x['meas_total'] for x in xs_ok])
    s = {k: sum(x[k] for x in xs) for k in F}
    r = lambda a, b: f'{s[a] / s[b]:.2f}' if s[b] else '—'  # noqa: E731
    med = lambda v: f'{np.median(v):+.3f}' if len(v) else '—'  # noqa: E731
    return (f"| {name} | {len(xs)} | {med(e)} | {med(en)} | {med(es)} | {r('pred_new', 'new_q_fp')} | "
            f"{r('new_q_fp', 'meas_new')} | {r('new_q', 'new_d')} | {r('G_total', 'new_q')} | {r('pred_total', 'meas_total')} |")


HEAD = ['| 分组 | 案例 | 相对误差中位 | 其中未见 key 部分 | 其中见过 key 部分 | 未见 key：预测 / 无缓存实测 | '
        '未见 key：无缓存 / 有缓存实测 | 未见 key 平均被查次数 | Good-Turing 未见查询量 / 实际 | 组内总预测 / 总实测 |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']


def main():
    S, Ss = defaultdict(list), defaultdict(list)
    for f in sorted(ROOT.glob('results/split_*_*.json')):
        if 'holdout' in f.name:
            continue
        for x in json.loads(f.read_text(encoding='utf-8')):
            for g in (grp(x['workload']), '合计'):
                (S if x['best10'] >= MIN_REF else Ss)[g].append(x)
    L = ['# RA6 预测偏高从哪里来：按学习期见过 / 没见过的 key 拆分', '',
         '对每个 E3 案例里 RA6 选中的结构（与 `report.md` 同一批案例），把预测和评估段实测的缺失数都拆成两部分：'
         '学习期见过的 key（按 Che 和 Good-Turing 速率预测，式 7）和学习期没见过的 key（G_i = H·N1/L·h_i 次查询乘分段 FPR，'
         '全部当作缓存挡不住，式 5）。未见 key 再给出无缓存时的实测误报（查询次数）和不同 key 数（有缓存时的下界）。'
         '相对误差 =（预测 − 实测）/ 实测，逐案例计算后取中位；它恰好等于"未见 key 部分"与"见过 key 部分"之和'
         '（两部分都除以同一个总实测），但三列的中位数不必相加相等。后面几列是组内求和后的比。', '',
         f'## 合成负载，前 10 最优 ≥{MIN_REF}', ''] + HEAD
    L += [line(g, S[g]) for g in ORDER if S.get(g)]
    L += ['', f'## 前 10 最优 <{MIN_REF}', ''] + HEAD + [line(g, Ss[g]) for g in ORDER if Ss.get(g)]
    hd = ROOT / 'results' / 'split_holdout_mawi2024_flow.json'
    if hd.exists():
        L += ['', '## MAWI 2024 留出集（诊断）', ''] + HEAD
        L += [line(f"{x['budget_kib']}KiB", [x]) for x in sorted(json.loads(hd.read_text()), key=lambda x: x['budget_kib'])]
    (ROOT / 'results' / 'bias_split.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
    print('\n'.join(L))


if __name__ == '__main__':
    main()
