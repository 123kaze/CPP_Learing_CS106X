"""Generate exact-only research tables/figures AFTER a complete independent audit.

No paper writes, no experiment imports, no old-prefix numerical reuse. All charts
have CSV twins. Static PNG/PDF output deliberately has no interactive web layer.
The scope is the FP matrix, not exclusive timing or all paper experiments.
"""
import os
for variable in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[variable] = '1'
import argparse
import csv
import hashlib
import importlib.util
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('audit55', HERE / 'audit55.py')
A = importlib.util.module_from_spec(spec)
spec.loader.exec_module(A)
GROUPS = ('1万', '10万', '100万', '全部', 'no-repeat', 'trace')
LABELS = {'1万': '10k-key pool', '10万': '100k-key pool', '100万': '1M-key pool',
          '全部': 'All keys', 'no-repeat': 'No repeats', 'trace': 'Real traces'}
BLUE, ORANGE, AQUA = '#257de0', '#f47230', '#00b894'
INK, SECONDARY, GRID = '#191919', '#666666', '#e7e7e7'


def ratio(a, b):
    return (a + 1) / (b + 1)


def median(values):
    return float(np.median(values)) if len(values) else None


def rowscsv(path, rows):
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open('x', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        for r in rows:
            w.writerow({k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v for k, v in r.items()})


def cohorts(case):
    c = case['case']
    if c['cohort'] != 'main':
        return ('MAWI24_posthoc',)
    if c['workload'] == A.PROBE:
        return ('probe',)
    ref = case['hindsight_h_fp'] if case['hindsight_h_fp'] is not None else case['R']['Replay']['fp']
    return ('all_nonprobe', 'eligible30_nonprobe') if ref >= 30 else ('all_nonprobe', 'low_reference_nonprobe')


def ranking_metrics(top):
    a = np.array([[r['stage1'], r['stage2'], r['fp']] for r in top], dtype=float)
    first = a[:5]; measured = first[:, 2]
    r = dict(best10_ge30=bool(a[:, 2].min() >= 30), best10_in_top5=bool(measured.min() == a[:, 2].min()), candidates=len(top))
    for col, name in ((0, 'stage1'), (1, 'stage2')):
        pred = first[:, col]
        defined = np.ptp(pred) > 0 and np.ptp(measured) > 0
        r[name + '_rho'] = float(spearmanr(pred, measured).statistic) if defined else None
        r[name + '_rho_undefined'] = not defined
        # Original Stage1 picks rank0, refined Stage2 breaks ties by original rank.
        pick = 0 if col == 0 else int(np.argmin(pred))
        r[name + '_picks_best'] = bool(measured[pick] == measured.min())
        ok = measured > 0
        r[name + '_relative_errors'] = ((pred[ok] - measured[ok]) / measured[ok]).tolist()
        r[name + '_zero_measured_excluded_from_relative_error'] = int((~ok).sum())
    return r


def main_tables(cases):
    by = defaultdict(list)
    for item in cases:
        c = item['case']
        if c['workload'] != A.PROBE:
            by[c['dataset'], c['budget_kib'], c['cohort']].append(item)
    out = []
    for (ds, kib, cohort), items in sorted(by.items()):
        by_w = defaultdict(list)
        for item in items:
            by_w[item['case']['workload']].append(item)
        values = {m: sum(float(np.mean([i['R'][m]['fp'] for i in v])) for v in by_w.values()) for m in A.METHODS}
        out.append(dict(dataset=ds, budget_kib=kib, cohort=cohort, cases=len(items), workloads=len(by_w),
                        bits_per_member=kib * 8192 / items[0]['members'],
                        RA_Replay_ratio=ratio(values['RA6'], values['Replay']), **values))
    return out


def case_tables(cases):
    out = []
    for co in ('all_nonprobe', 'eligible30_nonprobe', 'low_reference_nonprobe', 'probe', 'MAWI24_posthoc'):
        pool = [c for c in cases if co in cohorts(c)]
        for group in GROUPS + ('probe', 'TOTAL'):
            selected = [c for c in pool if group == 'TOTAL' or A.group(c['case']['workload']) == group]
            if not selected:
                continue
            r = dict(cohort=co, group=group, cases=len(selected))
            for method, baseline in (('RA6', 'Replay'), ('RA-stage1', 'Replay'), ('Gama+10%', 'Replay'),
                                     ('RA6-top3', 'Replay'), ('RA6-top10', 'Replay'), ('RA6', 'Gama'), ('RA6', 'BF+Exact'),
                                     ('RA6-warm', 'RA6'), ('Learned-stacked', 'RA6-warm')):
                v = np.array([ratio(c['R'][method]['fp'], c['R'][baseline]['fp']) for c in selected])
                stem = method + '/' + baseline
                r.update({stem + '_median': median(v), stem + '_p25': float(np.quantile(v, .25)), stem + '_p75': float(np.quantile(v, .75)), stem + '_worst': float(v.max()), stem + '_share_le1': float((v <= 1).mean())})
            hindsight = [c for c in selected if c['hindsight_h_fp'] is not None]
            r['hindsight_cases'] = len(hindsight)
            for method in ('RA6', 'Replay'):
                r[method + '/Hindsight_median'] = median([ratio(c['R'][method]['fp'], c['hindsight_h_fp']) for c in hindsight])
            out.append(r)
    return out


def ablation_tables(cases):
    detail = []
    by = defaultdict(list)
    for item in cases:
        c = item['case']
        if c['seed'] <= 2:
            by[c['dataset'], c['budget_kib'], c['workload'], c['cohort']].append(item)
    for (ds, kib, workload, co), items in sorted(by.items()):
        ref = float(np.mean([i['R']['RA-stage1']['fp'] for i in items]))
        for variant in sorted(A.ABLS | {'RA-global'}):
            vals = [i['R']['RA-global']['fp'] if variant == 'RA-global' else next(r['fp'] for r in i['ablations'] if r['variant'] == variant) for i in items]
            avg = float(np.mean(vals))
            detail.append(dict(dataset=ds, budget_kib=kib, workload=workload, cohort=co, seeds=len(items),
                               variant=variant, variant_seed_mean_fp=avg, stage1_seed_mean_fp=ref, ratio=ratio(avg, ref)))
    summary = []
    # Original report5.e6 includes probes. Preserve that scope AND publish nonprobe/probe separately.
    for scope in ('original_main_including_probe', 'main_nonprobe', 'probe', 'MAWI24_posthoc'):
        chosen = [r for r in detail if (r['cohort'] != 'main' if scope == 'MAWI24_posthoc' else r['cohort'] == 'main' and
                  (True if scope == 'original_main_including_probe' else r['workload'] == A.PROBE if scope == 'probe' else r['workload'] != A.PROBE))]
        for variant in sorted(A.ABLS | {'RA-global'}):
            selected = [r for r in chosen if r['variant'] == variant]
            if not selected:
                continue
            worst = max(selected, key=lambda r: r['ratio'])
            summary.append(dict(scope=scope, variant=variant, setting_workloads=len(selected),
                                median=median([r['ratio'] for r in selected]), worst=worst['ratio'],
                                trace_median=median([r['ratio'] for r in selected if r['dataset'].endswith('_flow')]),
                                worst_dataset=worst['dataset'], worst_budget_kib=worst['budget_kib'], worst_workload=worst['workload']))
    return detail, summary


def prediction_tables(cases):
    detail = []
    for item in cases:
        c = item['case']
        if c['cohort'] == 'main' and not c['dataset'].endswith('_flow') and 1 <= c['seed'] <= 4 and c['workload'] != A.PROBE:
            detail.append(dict(**{k: c[k] for k in A.IDENTITY}, group=A.group(c['workload']), **ranking_metrics(item['top10'])))
    summary = []
    for scope in ('best10_ge30', 'best10_lt30', 'all'):
        for group in GROUPS + ('TOTAL',):
            chosen = [r for r in detail if (group == 'TOTAL' or r['group'] == group) and
                      (scope == 'all' or r['best10_ge30'] == (scope == 'best10_ge30'))]
            if not chosen:
                continue
            row = dict(scope=scope, group=group, cases=len(chosen), best10_in_top5=float(np.mean([r['best10_in_top5'] for r in chosen])))
            for stage in ('stage1', 'stage2'):
                rho = [r[stage + '_rho'] for r in chosen if r[stage + '_rho'] is not None]
                errors = [v for r in chosen for v in r[stage + '_relative_errors']]
                row.update({stage + '_rho_median': median(rho), stage + '_rho_defined_cases': len(rho),
                            stage + '_rho_undefined_cases': len(chosen) - len(rho),
                            stage + '_picks_best_share': float(np.mean([r[stage + '_picks_best'] for r in chosen])),
                            stage + '_abs_relative_error_median': median(np.abs(errors)),
                            stage + '_signed_relative_error_median': median(errors),
                            stage + '_error_candidate_count': len(errors)})
            summary.append(row)
    return detail, summary


def chart_style():
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'axes.edgecolor': '#c2c2c2', 'axes.labelcolor': INK,
                         'text.color': INK, 'xtick.color': SECONDARY, 'ytick.color': SECONDARY,
                         'grid.color': GRID, 'grid.linewidth': .5, 'lines.linewidth': 1.5,
                         'pdf.fonttype': 42, 'savefig.facecolor': 'white'})


def savefigure(fig, out, name):
    for ext in ('png', 'pdf'):
        target = out / f'{name}.{ext}'
        A.check(not target.exists(), 'refuse figure overwrite')
        fig.savefig(target, dpi=160, bbox_inches='tight', pad_inches=.18)
    plt.close(fig)


def case_plot(cases, out, cohort):
    pool = [c for c in cases if cohort in cohorts(c)]
    fig, ax = plt.subplots(figsize=(10, 6), layout='constrained')
    source = []; rng = np.random.default_rng(5501); ticks = []; ticklabels = []
    for idx, g in enumerate(GROUPS):
        selected = [c for c in pool if A.group(c['case']['workload']) == g]
        if not selected:
            continue
        ticks.append(idx); ticklabels.append(f'{LABELS[g]}  (n={len(selected)})')
        for method, offset, col, marker in (('RA6', -.16, BLUE, 'o'), ('RA-stage1', .16, ORANGE, 's')):
            vals = np.array([ratio(c['R'][method]['fp'], c['R']['Replay']['fp']) for c in selected])
            y = idx + offset
            ax.scatter(vals, y + rng.uniform(-.055, .055, len(vals)), s=36, color=col, marker=marker,
                       alpha=.35, linewidths=.8, edgecolors='white', zorder=2)
            # Quantiles in log space match the original plotted IQR; tabular quantiles use raw ratios.
            q1, med, q3 = np.exp(np.quantile(np.log(vals), [.25, .5, .75]))
            ax.plot([q1, q3], [y, y], color=col, linewidth=2.5, zorder=3)
            ax.scatter([med], [y], s=46, color=col, marker='D', edgecolors='white', linewidths=1.2, zorder=4)
            if idx == 0:
                ax.annotate(method, (med, y), xytext=(8, -17 if offset < 0 else 12), textcoords='offset points', fontsize=9)
            for item, value in zip(selected, vals):
                source.append(dict(**{k: item['case'][k] for k in A.IDENTITY}, cohort=cohort, method=method,
                                   group=g, fp=item['R'][method]['fp'], replay_fp=item['R']['Replay']['fp'], ratio=float(value)))
    ax.axvline(1, color=SECONDARY, linewidth=.7, zorder=1)
    ax.set_xscale('log'); ax.grid(axis='x'); ax.set_yticks(ticks, ticklabels); ax.invert_yaxis()
    ax.set_xlabel('(FP + 1) / (Replay FP + 1), log scale; all observations shown')
    ax.set_title(f'Exact-key cache: {cohort} (n={len(pool)})', pad=14)
    ax.legend(handles=[Line2D([], [], color=BLUE, marker='o', label='RA6'), Line2D([], [], color=ORANGE, marker='s', label='Stage 1 only')], loc='lower right', frameon=False)
    rowscsv(out / f'case_ratios_{cohort}.csv', source)
    savefigure(fig, out, f'case_ratios_{cohort}')


def motivation(cases, out):
    workloads = ('每key一次', 'uniform-全部', 'zipf1.0-全部', 'zipf1.0-10万', 'zipf1.2-1万')
    titles = ('Each key once', 'Uniform, all keys', 'Zipf 1.0, all keys', 'Zipf 1.0, 100k', 'Zipf 1.2, 10k')
    shares = []
    for item in cases:
        c = item['case']
        if c['seed'] != 0 or not item['weighted_full']:
            continue
        by = defaultdict(list)
        for r in item['weighted_full']:
            by[r['frac']].append(r['fp'])
        best = min(min(v) for v in by.values())
        for frac in sorted(by):
            value = min(by[frac])
            shares.append(dict(dataset=c['dataset'], budget_kib=c['budget_kib'], workload=c['workload'],
                               bits_per_member=c['budget_kib'] * 8192 / item['members'], share=frac,
                               best_over_trees_fp=value, best_over_shares_fp=best, ratio=ratio(value, best)))
    rowscsv(out / 'motivation_all_best_by_share.csv', shares)
    fig, axes = plt.subplots(1, 5, figsize=(16, 3.8), layout='constrained', sharey=True)
    selected_source = []
    for ax, workload, title in zip(axes, workloads, titles):
        data = [r for r in shares if r['dataset'] == 'shalla' and r['budget_kib'] == 1024 and r['workload'] == workload]
        A.check(len(data) == 13, 'motivation fixed share grid')
        selected_source.extend(data)
        ax.plot([100 * r['share'] for r in data], [r['ratio'] for r in data], '-o', color=BLUE, markersize=6,
                markeredgecolor='white', markeredgewidth=1.2)
        best = min(data, key=lambda r: (r['best_over_trees_fp'], r['share']))
        ax.axvline(10, color=SECONDARY, linewidth=.7)
        ax.set_title(title, fontsize=10); ax.set_xscale('symlog', linthresh=.1, linscale=.3); ax.set_yscale('log')
        ax.set_xticks([0, .1, 1, 10, 60], ['0', '.1', '1', '10', '60']); ax.grid(axis='y')
        ax.set_xlabel('Cache share (%)')
        ax.text(.03, .96, f"Best share: {best['share']:.1%}", transform=ax.transAxes, va='top', fontsize=9)
    axes[0].set_ylabel('(FP + 1) / (best FP + 1)')
    fig.suptitle('Shalla 1024 KiB, seed 0: hindsight over all weighted candidates; vertical line = fixed 10%')
    rowscsv(out / 'motivation_share_selected.csv', selected_source)
    savefigure(fig, out, 'motivation_share')
    choices = [('shalla', workloads[0], titles[0]), ('shalla', workloads[2], titles[2]), ('shalla', workloads[3], titles[3]),
               ('caida_flow', '真实轨迹', 'CAIDA-flow'), ('mawi2021_flow', '真实轨迹', 'MAWI-21')]
    fig, axes = plt.subplots(1, 5, figsize=(16, 3.8), layout='constrained', sharey=True)
    source = []
    for ax, (ds, workload, title) in zip(axes, choices):
        by_budget = defaultdict(list)
        for r in shares:
            if r['dataset'] == ds and r['workload'] == workload:
                by_budget[r['budget_kib']].append(r)
        points = [min(v, key=lambda r: (r['best_over_trees_fp'], r['share'])) for _, v in sorted(by_budget.items())]
        A.check(len(points) == 4, 'motivation original four-budget scope')
        source.extend(points)
        ax.plot([r['bits_per_member'] for r in points], [r['share'] * 100 for r in points], '-o', color=BLUE,
                markersize=6, markeredgecolor='white', markeredgewidth=1.2)
        ax.set_xscale('log'); ax.set_ylim(-2, 64); ax.set_yticks([0, 20, 40, 60]); ax.grid(axis='y')
        ax.set_title(title); ax.set_xlabel('Budget (bits/member)')
    axes[0].set_ylabel('Hindsight best cache share (%)')
    fig.suptitle('Original Figure 1(b) workload scope; ties choose the smaller cache share')
    rowscsv(out / 'motivation_budget_selected.csv', source)
    savefigure(fig, out, 'motivation_budget')


def mawi_figures(cases, out):
    items = {i['case']['budget_kib']: i for i in cases if i['case']['cohort'] != 'main'}
    A.check(set(items) == {16, 24, 32, 128}, 'MAWI24 budget coverage')
    # Budget components are faceted, not a dual-axis memory/FP plot. Each panel
    # has one measure; the adjacent CSV retains all byte-level components.
    memory = []
    parts = [('model_bytes', 'Model arrays'), ('metadata_bytes', 'Region metadata'),
             ('array_overhead_bytes', 'Array headers'), ('filter_bytes', 'Packed Bloom filters'), ('cache_bytes', 'Exact-key cache')]
    fig, axes = plt.subplots(1, 6, figsize=(18, 5.2), layout='constrained', sharey=True)
    names = [f'{k} KiB / {m}' for k in (16, 24, 32) for m in ('Gama', 'Replay', 'RA6')]
    for ax, (part, title) in zip(axes[:5], parts):
        values = [items[k]['R'][m][part] / (k * 1024) * 100 for k in (16, 24, 32) for m in ('Gama', 'Replay', 'RA6')]
        ax.scatter(values, range(len(names)), s=40, color=BLUE, edgecolors='white', linewidths=1.2)
        ax.set_xlim(0, max(1, max(values) * 1.1)); ax.set_title(title); ax.set_xlabel('Budget share (%)'); ax.grid(axis='x')
    fps = [items[k]['R'][m]['fp'] + 1 for k in (16, 24, 32) for m in ('Gama', 'Replay', 'RA6')]
    axes[-1].scatter(fps, range(len(names)), s=40, color=BLUE, edgecolors='white', linewidths=1.2)
    axes[-1].set_xscale('log'); axes[-1].set_title('Evaluation false positives'); axes[-1].set_xlabel('FP + 1 (log scale)'); axes[-1].grid(axis='x')
    axes[0].set_yticks(range(len(names)), names); axes[0].invert_yaxis()
    fig.suptitle('Previously used MAWI24: exact-cache post-hoc recheck (original 16/24/32 KiB split scope)')
    savefigure(fig, out, 'mawi24_memory')
    for k, item in sorted(items.items()):
        for m in ('Gama', 'Replay', 'RA6'):
            row = item['R'][m]
            memory.append(dict(budget_kib=k, method=m, fp=row['fp'], total_bytes=row['total_bytes'], unused_bytes=k * 1024 - row['total_bytes'], **{p: row[p] for p, _ in parts}))
    rowscsv(out / 'mawi24_memory_and_fp.csv', memory)
    fig, axes = plt.subplots(1, 4, figsize=(14, 3.8), layout='constrained')
    predsource = []
    for ax, (k, item) in zip(axes, sorted(items.items())):
        data = item['weighted_full']; selected = item['R']['RA6']
        x = np.array([r['stage2'] + 1 for r in data]); y = np.array([r['fp'] + 1 for r in data])
        ax.scatter(x, y, s=36, color=BLUE, alpha=.45, edgecolors='white', linewidths=.8)
        low, high = min(x.min(), y.min()) * .8, max(x.max(), y.max()) * 1.25
        ax.plot([low, high], [low, high], color=SECONDARY, linewidth=.7)
        chosen = next(r for r in data if (r['trees'], r['frac']) == (selected['trees'], selected['frac']))
        ax.scatter([chosen['stage2'] + 1], [chosen['fp'] + 1], s=100, color=ORANGE, marker='*', edgecolors='white', linewidths=1)
        ax.annotate('Chosen RA6', (chosen['stage2'] + 1, chosen['fp'] + 1), xytext=(6, 7), textcoords='offset points', fontsize=8)
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xlim(low, high); ax.set_ylim(low, high)
        ax.set_title(f'{k} KiB (n={len(data)})'); ax.set_xlabel('Refined prediction + 1'); ax.grid()
        for r in data:
            predsource.append(dict(budget_kib=k, selected=(r is chosen), **r))
    axes[0].set_ylabel('Measured FPs + 1')
    fig.suptitle('Previously used MAWI24, exact cache: all weighted candidates (not a new holdout)')
    axes[-1].legend(handles=[Line2D([], [], color=BLUE, marker='o', linestyle='', label='All candidates'),
                             Line2D([], [], color=ORANGE, marker='*', linestyle='', label='Chosen RA6')], frameon=False, fontsize=8)
    rowscsv(out / 'mawi24_predictions.csv', predsource)
    savefigure(fig, out, 'mawi24_predictions')


def main():
    started = time.perf_counter()
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--round', type=Path, required=True)
    p.add_argument('--audit', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    root, out = args.round.resolve(), args.out.resolve()
    audit = A.read(args.audit / 'verification.json')
    A.check(audit['status'] == 'complete_evidence_audit_passed' and audit['cases'] == 1150, 'complete independent audit required')
    hashes = A.read(args.audit / 'evidence_hashes.json')
    bloom = root.parents[1]
    cases = []
    for name, digest in hashes['case_files'].items():
        path = bloom / name
        A.check(A.sha(path) == digest, 'audited case changed')
        item = A.read(path)
        item['R'] = {r['method']: r for r in item['rows']}
        item['members'] = A.read(path.parent / 'status.json')['input']['members']
        cases.append(item)
    A.check(len(cases) == 1150, 'artifact case scope')
    out.mkdir(parents=True, exist_ok=False)
    chart_style()
    rowscsv(out / 'table2_main_totals.csv', main_tables(cases))
    rowscsv(out / 'table3_case_ratios.csv', case_tables(cases))
    detail, summary = ablation_tables(cases)
    rowscsv(out / 'table7_ablation_seed_means.csv', detail); rowscsv(out / 'table7_ablation_summary.csv', summary)
    detail, summary = prediction_tables(cases)
    rowscsv(out / 'prediction_per_case.csv', detail); rowscsv(out / 'prediction_summary.csv', summary)
    case_plot(cases, out, 'eligible30_nonprobe'); case_plot(cases, out, 'all_nonprobe')
    motivation(cases, out); mawi_figures(cases, out)
    with (out / 'README.md').open('x', encoding='utf-8') as f:
        f.write('# 第55轮 exact-key 主FP表图\n\n所有数值来自完整1150例的独立核验档案；旧prefix数值没有复制。\n\n'
                '- Table2：每workload先seed均值，再求和，probe不入总表；MAWI24四例单列。\n'
                '- Table3/Figure4：新reference≥30子集和所有1076非probe并列；不复用旧748。图显示全部点，不复用旧固定横轴裁切。\n'
                '- Table7：先对seed0–2求均值再平滑作比。旧report5.e6实际含probe，因此同时提供含probe原范围、非probe与probe三种明确标签；MAWI24单列。\n'
                '- 预测表：静态seed1–4；前10实测最优≥30是此表自己的筛选规则，不与Table3 reference混用。指标在前5内，常数向量相关性留空并记数量，相对误差只排除实测0的候选。\n'
                '- Figure1：复核原五负载与原三条Shalla负载＋两条flow；每share取树数最优，全部为hindsight而非在线选择。为避免拥挤改为小多图。\n'
                '- Figure5：内存拆分保留原16/24/32范围，完整CSV加128；候选预测包含四预算。用分面字节组成点图及独立FP面板而非双轴；精确FP在CSV。MAWI24已使用，非新独立holdout。\n'
                '- 每图都有CSV数据；静态PNG/PDF，使用形状/分面/文字作为颜色以外的识别通道。彩色方案已验证；橙/青色对比度警告由数据表和文字标签补足。\n'
                '- 本脚本不生成新的独占选择/训练构建/规模计时，也不修改论文或发布。\n\n'
                '**生成不等于视觉核验：必须逐图打开PNG检查后，才可将渲染检查打勾。**\n')
    A.writejson(out / 'generation.json', dict(status='generated_visual_inspection_pending', cases=1150, script_sha256=A.sha(Path(__file__)),
                auditor_sha256=hashes['auditor_sha256'], generation_s=time.perf_counter()-started,
                files={p.name: A.sha(p) for p in sorted(out.iterdir()) if p.is_file()}))
    print('EXACT_ARTIFACTS_GENERATED; visual inspection still required:', out)


if __name__ == '__main__':
    main()
