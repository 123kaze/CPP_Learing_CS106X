"""E3 for RA6's predictor (bucket load) inside RA4's shortlist, from results/verify_bucket/*.json
(RA4 top 10 per seed-0 E3 case, each built and measured) and the all-candidate measurements in
results/e3_*.jsonl. Writes results/e3_ra6.md."""
import json
import glob
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.stats import spearmanr

ROOT = Path(__file__).resolve().parents[1]


def grp(w):
    if w == '真实轨迹':
        return '真实轨迹'
    for p in ('1万', '10万', '100万', '全部'):
        if w.endswith('-' + p):
            return p + ' key 池'
    return '每key一次/全新对抗'


best_all = {}
for f in glob.glob(str(ROOT / 'results' / 'e3_*.jsonl')):
    ds, kib = Path(f).stem[3:].rsplit('_', 1)
    for line in open(f, encoding='utf-8'):
        r = json.loads(line)
        if r['seed'] == 0:
            best_all[ds, kib, r['workload']] = min(c['measured'] for c in r['candidates'])
S = defaultdict(lambda: defaultdict(list))
for f in glob.glob(str(ROOT / 'results' / 'verify_bucket' / '*.json')):
    ds, kib = Path(f).stem.rsplit('_', 1)
    for r in json.load(open(f, encoding='utf-8')):
        rows = r['rank_rows']          # (trees, frac, RA4 pred, bucket-load pred, measured) in RA4 order
        meas = np.array([x[4] for x in rows], float)
        pr = np.array([x[2] for x in rows], float)
        pd = np.array([x[3] for x in rows], float)
        ba = best_all.get((ds, kib, r['workload']), meas.min())
        m5, p5, d5 = meas[:5], pr[:5], pd[:5]
        for g in (grp(r['workload']), '合计'):
            s = S[g]
            if np.ptp(m5) > 0:
                if np.ptp(p5) > 0:
                    s['rho_RA4'].append(spearmanr(p5, m5).statistic)
                if np.ptp(d5) > 0:
                    s['rho_D'].append(spearmanr(d5, m5).statistic)
            s['recall5'].append(ba in m5)
            s['recall10'].append(ba in meas)
            s['top1_D'].append(m5[np.argmin(d5)] == m5.min())
            s['top1_RA4'].append(m5[0] == m5.min())
            ok = m5 > 0
            s['relD'] += list(np.abs(d5[ok] - m5[ok]) / m5[ok])
            s['relRA4'] += list(np.abs(p5[ok] - m5[ok]) / m5[ok])
L = ['# E3：RA6 预测器的准确度（在 RA4 排名前 5 的候选内）', '',
     '数据：第五轮种子 0 的全部 E3 案例（探测重放除外）。每个案例取 RA4 预测的前 10 个候选，逐个建出结构，'
     '在评估段实测（`results/verify_bucket/`）；"全局最优"是该案例全部约 150 个候选里实测最好的那个。', '',
     '| 分组 | 案例 | 全局最优在前 5 / 前 10 | 前 5 内 Spearman：RA4 → RA6 | 前 5 内选中最优：RA4 → RA6 | 前 5 内相对误差中位：RA4 → RA6 |',
     '|---|---:|---:|---:|---:|---:|']
for g in ('1万 key 池', '10万 key 池', '100万 key 池', '全部 key 池', '每key一次/全新对抗', '真实轨迹', '合计'):
    s = S.get(g)
    if not s:
        continue
    L.append(f"| {g} | {len(s['recall5'])} | {np.mean(s['recall5']):.0%} / {np.mean(s['recall10']):.0%} | "
             f"{np.median(s['rho_RA4']):.3f} → {np.median(s['rho_D']):.3f} | {np.mean(s['top1_RA4']):.0%} → {np.mean(s['top1_D']):.0%} | "
             f"{np.median(s['relRA4']):.3f} → {np.median(s['relD']):.3f} |")
(ROOT / 'results' / 'e3_ra6.md').write_text('\n'.join(L) + '\n', encoding='utf-8')
print('\n'.join(L))
