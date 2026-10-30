"""Summary of the option-D offline check (results/verify_bucket/*.json) by key pool."""
import json
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def group(w):
    if w == '真实轨迹':
        return '真实轨迹'
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p
    return '每key一次/全新对抗'


def ratio(a, b):
    return (a + 1) / (b + 1)


recs = []
for f in sorted((ROOT / 'results' / 'verify_bucket').glob('*.json')):
    ds, kib = f.stem.rsplit('_', 1)
    for r in json.loads(f.read_text(encoding='utf-8')):
        r['setting'] = f'{ds} {kib}'
        recs.append(r)
G = defaultdict(list)
for r in recs:
    G[group(r['workload'])].append(r)
    G['全部案例'].append(r)
lines = ['| 分组 | 案例 | RA4/网格 中位 | 最坏 | D5/网格 中位 | 最坏 | D5 ≤ 网格 | D5/表内最优 中位 | D5 命中表内最优 | RA4 命中 |',
         '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
for g in ('1万', '10万', '100万', '全部', '每key一次/全新对抗', '真实轨迹', '全部案例'):
    rs = G.get(g)
    if not rs:
        continue
    ra = np.array([ratio(r['ra4'], r['grid']) for r in rs])
    d5 = np.array([ratio(r['D5'], r['grid']) for r in rs])
    db = np.array([ratio(r['D5'], r['best_measured']) for r in rs])
    lines.append(f"| {g} | {len(rs)} | {np.median(ra):.3f} | {ra.max():.3f} | {np.median(d5):.3f} | {d5.max():.3f} | "
                 f"{np.mean(d5 <= 1):.0%} | {np.median(db):.3f} | {np.mean([r['D5'] == r['best_measured'] for r in rs]):.0%} | "
                 f"{np.mean([r['ra4'] == r['best_measured'] for r in rs]):.0%} |")
worst = sorted(recs, key=lambda r: -ratio(r['D5'], r['grid']))[:8]
lines += ['', 'D5 相对网格最差的案例：', '']
lines += [f"- {r['setting']} {r['workload']}：网格 {r['grid']:,}，RA4 {r['ra4']:,}，D5 {r['D5']:,}，表内最优 {r['best_measured']:,}" for r in worst]
text = '\n'.join(lines)
(ROOT / 'results' / 'verify_bucket' / 'summary.md').write_text(text + '\n', encoding='utf-8')
print(text)
