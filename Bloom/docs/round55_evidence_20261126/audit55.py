"""Read-only audit of round55; never imports its experiment modules or rewrites results.

--partial checks only atomically completed cases and source hashes; it is not a
full-campaign certificate. Final mode requires completion, hashes all frozen
inputs, and checks the generated CSVs against the per-case JSON evidence.
Output must be a NEW directory. Run with Python -I.
"""
import argparse
import csv
import hashlib
import json
import math
import statistics
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

PROBE = '探测重放10%'
MAIN = ('Gama', 'Gama+10%', 'Replay', 'RA-stage1', 'RA-global', 'RA6-top3',
        'RA6', 'RA6-top10', 'PlainBF', 'BF+Exact')
METHODS = MAIN + ('RA6-warm', 'Replay-warm', 'BF+Exact-warm', 'Learned-stacked')
ABLS = {'noRepeat', 'noSA', 'noGT', 'mix0.5', 'mix1', 'Table-exact-adapter'}
PARTS = ('model_bytes', 'filter_bytes', 'metadata_bytes', 'array_overhead_bytes', 'cache_bytes')
IDENTITY = ('dataset', 'budget_kib', 'workload', 'seed')


def check(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def readcsv(path):
    with path.open(newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def writejson(path, obj):
    with path.open('x', encoding='utf-8') as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, allow_nan=False)
        f.write('\n')


def writecsv(path, rows):
    fields = sorted(set().union(*(r.keys() for r in rows)))
    with path.open('x', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator='\n')
        w.writeheader()
        w.writerows(rows)


def key(case):
    return tuple(case[k] for k in IDENTITY)


def width(ds):
    return 8 if ds in ('cod', 'caida') else 33 if ds == 'caida_flow' else 9 if ds.endswith('_flow') else 128


def group(workload):
    if workload == PROBE:
        return 'probe'
    if workload == '真实轨迹':
        return 'trace'
    if workload in ('每key一次', '全新对抗'):
        return 'no-repeat'
    return workload.rsplit('-', 1)[-1]


def audit_row(row, case, tail_queries):
    budget = case['budget_kib'] * 1024
    check(row['member_fn'] == row['member_index_bytes'] == 0, 'FN/index assertion')
    check(0 <= row['total_bytes'] <= budget == row['budget_bytes'], 'budget accounting')
    check(isinstance(row['fp'], int) and 0 <= row['fp'] <= tail_queries, 'FP range')
    if row.get('method') == 'Learned-stacked':
        check(row['layers']['baseline_source'] == 'frozen round6 stacked_full.stacked_fp', 'stacked provenance')
        return
    check(sum(row[p] for p in PARTS) == row['total_bytes'], 'ledger sum')
    check(all(isinstance(row[p], int) and row[p] >= 0 for p in PARTS), 'physical ledger types')
    cb, slots = row['cache_bytes'], row['cache_slots']
    stride = 4 * (width(case['dataset']) + 4) + 1
    check(slots >= 0 and slots % 4 == 0, 'whole four-way buckets')
    check(cb == (112 + 32 + stride * (slots // 4) if slots else 0), 'exact-key physical bytes')
    check(row['fp'] == row['inserts'] + row['bypass'], 'FP insertion/bypass accounting')
    check(0 <= row['evictions'] <= row['inserts'] and 0 <= row['hits'] <= tail_queries - row['fp'], 'cache counter ranges')
    check(len(row['cache_sha']) == len(row['flags_sha']) == 64, 'state digest length')
    check(row['tail_replay_s'] >= 0 and row['member_check_s'] >= 0, 'measured stage times')


def audit_case(item, case):
    check(item['status'] == 'complete' and item['case'] == case, 'case identity')
    rows = {r['method']: r for r in item['rows']}
    check(len(item['rows']) == len(rows) == 14 and set(rows) == set(METHODS), 'exact 14-method coverage')
    H = item['tail_queries']
    check(item['learning_queries'] > 0 and H > 0, 'nonempty windows')
    check(item['learning_queries'] == (item['learning_queries'] + H) // 4, 'shared quarter split')
    for r in item['rows']:
        check(key(r) == key(case) and r['tail_queries'] == H, 'row identity/window')
        audit_row(r, case, H)
    g = rows['Gama']
    check((g['fp'], g['trees']) == (case['historical_Gama_fp'], case['historical_Gama_trees']), 'historical Gama regression')
    check(g['cache_bytes'] == 0 and rows['PlainBF']['cache_bytes'] == 0, 'uncached baselines')
    check(rows['PlainBF']['model_bytes'] == rows['BF+Exact']['model_bytes'] == 0, 'model-free baselines')
    if 'historical_stacked_fp' in case:
        check(rows['Learned-stacked']['fp'] == case['historical_stacked_fp'], 'historical stacked regression')
        check(rows['Learned-stacked']['historical_stacked_regression'], 'stacked regression marker')
    for name in ('RA6', 'Replay', 'BF+Exact'):
        cold, warm = rows[name], rows[name + '-warm']
        for field in PARTS + ('trees', 'frac', 'cache_slots', 'flags_sha', 'total_bytes'):
            check(cold[field] == warm[field], 'warm/cold share selected structure')
        check(cold['phase'] == 'cold' and warm['phase'] == 'warm', 'warm/cold phases')
        check(cold['learning_warm_s'] == 0 and warm['learning_warm_s'] > 0, 'actual learning replay recorded')
    top = item['top10']
    check(len(top) == 10 and [r['rank'] for r in top] == list(range(10)), 'top10 coverage/order')
    check(len({(r['trees'], r['frac']) for r in top}) == 10, 'top10 unique candidates')
    for name, k in (('RA-stage1', 1), ('RA6-top3', 3), ('RA6', 5), ('RA6-top10', 10)):
        predfield = 'stage1' if k == 1 else 'stage2'
        chosen = min(top[:k], key=lambda r: (r[predfield], r['rank']))
        actual = rows[name]
        check((actual['trees'], actual['frac'], actual['fp']) == (chosen['trees'], chosen['frac'], chosen['fp']), 'prediction-only shortlist choice')
        check(actual['selection_info']['pred'] == chosen[predfield], 'chosen prediction')
    for name, field in (('Replay', 'learning_Replay_records'), ('BF+Exact', 'learning_BF_records')):
        candidates = item[field]
        selected = [r for r in candidates if (r['trees'], r['frac']) == (rows[name]['trees'], rows[name]['frac'])]
        check(len(selected) == 1 and not selected[0]['cutoff'], 'selected replay candidate not cut off')
        check(selected[0]['fp'] == min(r['fp'] for r in candidates if not r['cutoff']), 'learning FP minimum; est_fpr tiebreak not independently recorded')
    ab = item['ablations']
    check(len(ab) == (6 if case['seed'] <= 2 else 0), 'ablation seed scope')
    if ab:
        check({r['variant'] for r in ab} == ABLS, 'ablation methods')
        for r in ab:
            audit_row(r, case, H)
    oracle = item['hindsight_h_records']
    if case['seed'] <= 2:
        check({(r['trees'], r['frac']) for r in oracle} == {(r['trees'], r['frac']) for r in item['learning_Replay_records']}, 'hindsight full h-grid')
        check(item['hindsight_h_fp'] == min(r['fp'] for r in oracle), 'hindsight minimum')
        replay_tail = next(r for r in oracle if (r['trees'], r['frac']) == (rows['Replay']['trees'], rows['Replay']['frac']))
        check(replay_tail['fp'] == rows['Replay']['fp'], 'hindsight replay candidate consistency')
    else:
        check(not oracle and item['hindsight_h_fp'] is None, 'no invented hindsight for seeds3/4')
    full = item['weighted_full']
    if case['seed'] == 0:
        check(len(full) >= 10 and len({(r['trees'], r['frac']) for r in full}) == len(full), 'full weighted candidate coverage')
        shortlist = sorted(full, key=lambda r: (r['stage1'], r['trees'], r['frac']))[:10]
        for a, b in zip(shortlist, top):
            check(all(a[f] == b[f] for f in ('trees', 'frac', 'stage1', 'stage2', 'fp')), 'full-grid and top10 consistency')
    else:
        check(not full, 'full-grid diagnostics seed0 only')
    return rows


def archived_cases(bloom):
    wr = bloom / 'windows_research'
    expected = {}
    for p in sorted((wr / 'round6_bucket/results/main').glob('rows_*.csv')):
        source = [r for r in readcsv(p) if r['method'] == 'RA6']
        check(bool(source), 'empty old setting')
        ds, kib = source[0]['dataset'], int(source[0]['budget_kib'])
        old_g = {(r['workload'], int(r['seed'])): r for r in readcsv(wr / f'round5_dp/results/rows_{ds}_{kib}.csv') if r['method'] == 'Gama'}
        old_s = {(r['workload'], int(r['seed'])): r for r in readcsv(wr / f'round6_bucket/results/stacked/rows_{ds}_{kib}.csv')}
        for r in source:
            pair = r['workload'], int(r['seed'])
            c = dict(dataset=ds, budget_kib=kib, workload=pair[0], seed=pair[1], cohort='main',
                     historical_Gama_fp=int(old_g[pair]['fp_tail']), historical_Gama_trees=int(old_g[pair]['trees']), historical_stacked_fp=int(old_s[pair]['fp_tail']))
            check(key(c) not in expected, 'old duplicate case')
            expected[key(c)] = c
    check(len(expected) == 1146, 'old1146 coverage')
    for k in (16, 24, 32, 128):
        p = wr / f'round6_bucket/results/holdout/round5_methods/rows_mawi2024_flow_{k}.csv'
        g = next(r for r in readcsv(p) if r['method'] == 'Gama')
        c = dict(dataset='mawi2024_flow', budget_kib=k, workload='真实轨迹', seed=0, cohort='previously_used_MAWI24', historical_Gama_fp=int(g['fp_tail']), historical_Gama_trees=int(g['trees']))
        expected[key(c)] = c
    return expected


def csv_equal(path, expected):
    actual = readcsv(path)
    check(len(actual) == len(expected), f'{path.name} length')
    for got, want in zip(actual, expected):
        for field, value in want.items():
            serialized = json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else '' if value is None else str(value)
            check(got[field] == serialized, f'{path.name}: {field}')
        check(all(not v for k, v in got.items() if k not in want), f'{path.name} unexpected value')


def run(root, out, partial):
    start = time.perf_counter()
    bloom = root.parents[1]
    freeze = read(root / 'plan/freeze.json')
    manifest = read(root / 'plan/cases.json')
    expected = archived_cases(bloom)
    recorded = {key(c): c for s in manifest['settings'] for c in s['cases']}
    check(recorded == expected and len(manifest['settings']) == 34, 'manifest vs independent historical source reconstruction')
    check(sum(c['workload'] == PROBE for c in expected.values()) == 70, '70-probe scope')
    source_hashes = {}
    for name, digest in freeze['sources'].items():
        check(sha(bloom / name) == digest, 'source hash: ' + name)
        source_hashes[name] = digest
    check(not (root / 'results/failure.json').exists(), 'campaign failure present; do not certify')
    if not partial:
        check(read(root / 'results/completion.json')['status'] == 'complete', 'campaign incomplete')
    input_hashes = {}
    if not partial:
        for name, digest in freeze['inputs'].items():
            check(sha(bloom / name) == digest, 'input hash: ' + name)
            input_hashes[name] = digest
    files = {}; verified = []; allrows = []; allabl = []; alltop = []; allfull = []; setting_states = []
    regressions53 = 0; completed_settings = 0
    for setting in manifest['settings']:
        ds, kib = setting['dataset'], setting['budget_kib']
        folder = root / f'results/{ds}_{kib}'
        sp = folder / 'status.json'
        if not sp.exists():
            check(partial, 'missing setting: ' + folder.name)
            setting_states.append(dict(setting=folder.name, status='not_started', cases=0))
            continue
        meta = read(sp)
        check(not meta['pilot'] and meta['input']['member_index_required_bytes'] == 0 and meta['input']['width'] == width(ds), 'formal no-index input metadata')
        names = meta['case_files']
        check(names == [f'case_{i:03d}.json' for i in range(len(names))], 'case sequence')
        check(len(names) <= len(setting['cases']), 'extra case files')
        if meta['status'] == 'complete':
            check(len(names) == meta['cases_completed'] == len(setting['cases']), 'complete setting size')
            check(meta['peak_rss_bytes'] < 8 * 1024**3, 'host RSS bound')
            completed_settings += 1
        else:
            check(partial and meta['status'] == 'running', 'incomplete setting')
        setting_states.append(dict(setting=folder.name, status=meta['status'], cases=len(names)))
        prior53 = bloom / f'windows_research/round53_index_free_recheck_v4/results/{ds}_{kib}.json'
        rr53 = read(prior53)['rows'] if prior53.exists() else []
        for name, case in zip(names, setting['cases']):
            file = folder / name
            item = read(file)
            rows = audit_case(item, case)
            needs53 = case['seed'] == 0 and case['workload'] in ('每key一次', 'uniform-全部', 'zipf1.0-全部', '真实轨迹') and prior53.exists()
            check(item['regression53'] == needs53, 'round53 required regression coverage')
            if item['regression53']:
                regressions53 += 1
                for m in ('Gama', 'Gama+10%', 'Replay', 'RA6', 'RA-global', 'PlainBF', 'BF+Exact'):
                    oldname = 'RA-PLBF-GT19' if m == 'RA6' else m
                    old = next(r for r in rr53 if r['method'] == oldname and r['workload'] == case['workload'])
                    new = rows[m]
                    for a, b in (('trees', 'trees'), ('frac', 'frac'), ('fp', 'fp'), ('flags_sha', 'static_flags_sha256'), ('cache_sha', 'cache_sha256'), ('total_bytes', 'total_bytes')):
                        check(new[a] == old[b], 'round53 regression')
            files[str(file.relative_to(bloom))] = sha(file)
            ref = item['hindsight_h_fp'] if item['hindsight_h_fp'] is not None else rows['Replay']['fp']
            base = {k: case[k] for k in IDENTITY + ('cohort',)}
            verified.append(dict(**base, group=group(case['workload']), reference_fp=ref, eligible_reference30=ref >= 30, learning_queries=item['learning_queries'], tail_queries=item['tail_queries'], source=str(file.relative_to(bloom)), **{m: rows[m]['fp'] for m in METHODS}))
            allrows.extend(dict(cohort=case['cohort'], **r) for r in item['rows'])
            allabl.extend(dict(**base, reference_stage1_fp=rows['RA-stage1']['fp'], **a) for a in item['ablations'])
            alltop.extend(dict(**base, **r) for r in item['top10'])
            allfull.extend(dict(**base, **r) for r in item['weighted_full'])
    check(len({key(c) for c in verified}) == len(verified), 'audited unique keys')
    if not partial:
        check(len(verified) == 1150 and completed_settings == 34, 'full coverage')
        for name, rows in (('rows.csv', allrows), ('ablations.csv', allabl), ('top10_predictions.csv', alltop), ('full_weighted_predictions.csv', allfull)):
            csv_equal(root / 'results' / name, rows)
        totals = readcsv(root / 'results/table_main_totals.csv')
        check(len(totals) == 34 * 14, 'main totals coverage')
        for row in totals:
            case_rows = [c for c in verified if c['dataset'] == row['dataset'] and c['budget_kib'] == int(row['budget_kib']) and c['group'] != 'probe']
            by = defaultdict(list)
            for c in case_rows:
                by[c['workload']].append(c[row['method']])
            want = sum(statistics.fmean(values) for values in by.values())
            check(math.isclose(want, float(row['FP_sum_of_seed_means']), rel_tol=1e-12, abs_tol=1e-9), 'seed-mean main total')
    report = dict(status='partial_evidence_checked_not_campaign_complete' if partial else 'complete_evidence_audit_passed',
                  created_utc=datetime.now(timezone.utc).isoformat(), cases=len(verified), expected=1150,
                  completed_settings=completed_settings, by_dataset=dict(Counter(c['dataset'] for c in verified)),
                  main_cases=sum(c['cohort'] == 'main' for c in verified), probe_cases=sum(c['group'] == 'probe' for c in verified),
                  rows=len(allrows), ablations=len(allabl), top10_records=len(alltop), weighted_records=len(allfull),
                  Gama_regressions=len(verified), stacked_regressions=sum(c['cohort'] == 'main' for c in verified), round53_case_regressions=regressions53,
                  source_hashes_checked=len(source_hashes), input_hashes_checked=len(input_hashes), input_hashes_deferred=len(freeze['inputs']) if partial else 0,
                  checks=['historical case identity', 'physical cache formula, all ledger sums', 'recorded member FN/index=0', 'Gama/stacked/round53 regressions', 'actual warm replay markers', 'prediction-only shortlist choices', 'learning replay minima', 'hindsight scope/minimum', 'weighted vs top10 consistency'],
                  limitations=['This is independent archive/hash/arithmetic validation, not a second execution of the complete query streams.',
                               'Replay est_fpr tie-break is not stored in per-candidate learning records and is not independently reconstructed.',
                               'Concurrent process times are not uncontended construction/selection benchmarks.',
                               'Input hashes are deferred in partial mode; no complete campaign claim.',
                               'Static same-version keys, exact negative feedback before cache insertion; long keys bypass.'],
                  settings=setting_states, elapsed_s=time.perf_counter()-start)
    writecsv(out / 'verified_cases.csv', verified)
    writejson(out / 'evidence_hashes.json', dict(auditor_sha256=sha(Path(__file__)), frozen_sources=source_hashes, frozen_inputs=input_hashes, case_files=files))
    writejson(out / 'verification.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ('settings', 'checks', 'limitations')}, ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--round', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--partial', action='store_true')
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    try:
        run(a.round.resolve(), a.out.resolve(), a.partial)
    except Exception as e:
        writejson(a.out / 'audit_failure.json', dict(status='failed', error_type=type(e).__name__, error=str(e)))
        raise


if __name__ == '__main__':
    main()
