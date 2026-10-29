"""C2-C4: RA-PLBF against Gama, StreamModel, LearnGrid and Fixed48Grid on identical streams.

Same protocol as round2 run_main: first 25% learning, last 75% evaluated with a
cold cache, physical byte accounting, deployment sketch not charged.
Checkpointed after every (workload, seed).
"""
import argparse
import json
import time
import numpy as np
import ra_plbf as RA

E, C = RA.E, RA.C
VARIANTS = (('RA-PLBF', 'ra', 'emp'), ('RA-Zipf', 'ra', 'zipf'),
            ('RA-NoRepeat', 'norepeat', 'emp'), ('RA-GlobalCache', 'global', 'emp'))


def run(ds, budgets, queries, seeds, only=None, tag='main', variants=VARIANTS):
    setup, scores, safe = E.load(ds)
    out = RA.ROOT / 'results' / tag / ds
    out.mkdir(parents=True, exist_ok=True)
    E.OLD._measure(np.zeros(0, np.int64), setup.h1q, np.zeros(len(setup.h1q), np.bool_))
    E.F.simulate(np.zeros(0, np.int64), setup.h1q, safe, np.zeros(len(setup.h1q), np.bool_), 4096)
    specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    if only:
        specs = [w for w in specs if w[0] in only]
    if ds.endswith('_flow'):
        seeds = 1
    for kib in budgets:
        dest = out / f'{kib}.json'
        prev = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[], selections=[], completed=False)
        if prev['completed']:
            continue
        rows, details = prev['rows'], prev['selections']
        done = {(r['workload'], r['seed']) for r in details}
        t = time.perf_counter()
        cands = E.candidates(setup, scores, kib)
        build_seconds = time.perf_counter() - t
        zeros = [c for c in cands if c['frac'] == 0]
        gama = min(zeros, key=lambda c: (c['structure'].est_fpr, c['trees']))
        probe = max((c for c in zeros if c['trees'] <= 48), key=lambda c: c['trees'])
        bins = E.BinMemo()
        for name, spec, family in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                start = time.perf_counter()
                stream = E.stream_for(setup, name, spec, family, seed, queries, gama['structure'])
                learn_n = len(stream) // 4
                learn, tail = stream[:learn_n], stream[learn_n:]
                ts = time.perf_counter()
                stats = E.measure(learn, setup, probe['structure'])
                ranking = E.rank(cands, stats, probe['structure'], len(tail), learn_n, bins)
                model, model_seconds = ranking[0][-1], time.perf_counter() - ts
                grid, fixed, grid_seconds, _ = E.exact_grid(ranking, learn, setup, safe)
                methods = [('Gama', gama, 0., None), ('StreamModel', model, model_seconds, None),
                           ('LearnGrid', grid, grid_seconds, None), ('Fixed48Grid', fixed, grid_seconds, None)]
                ts = time.perf_counter()
                lm = RA.summarize(learn)
                summary_seconds = time.perf_counter() - ts
                for method, mode, pop in variants:
                    c, info = RA.select(setup, scores, lm, kib, len(tail), mode, pop, bins)
                    info['selection_seconds'] += summary_seconds
                    methods.append((method, c, info['selection_seconds'], info))
                    if method == 'RA-PLBF':
                        chosen, guard = RA.guarded(setup, scores, safe, learn, kib, len(tail), gama, c, bins)
                        guard_entry = ('RA-PLBF+G', chosen, info['selection_seconds'] + guard['guard_seconds'], None)
                methods.append(guard_entry)
                frequencies = np.bincount(tail, minlength=len(setup.h1q))
                sel = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, queries=len(stream),
                           learning_queries=learn_n, learning_distinct_keys=len(lm.keys),
                           learning_state_bytes=lm.state_bytes, shared_build_seconds=build_seconds, ra={},
                           guard=guard)
                for method, c, seconds, info in methods:
                    if c is None:
                        continue
                    result = E.evaluate(c, tail, setup, safe, frequencies)
                    r = E.row(c, result, ds, kib, name, seed, method, len(stream), learn_n, seconds)
                    r['member_index_bytes'] = setup.member_hashes.nbytes
                    r['learning_trace_bytes'] = learn.nbytes if 'Grid' in method else 0
                    if method == 'RA-PLBF+G':
                        r['learning_state_bytes'] = lm.state_bytes + learn.nbytes // 4
                        r['guard_kept_ra'] = guard['kept_ra']
                    if info is not None:
                        seg_fp, seg_static, hits = RA.measure_segments(c, tail, setup, safe)
                        assert int(seg_fp.sum()) == result['fp'], (method, seg_fp.sum(), result['fp'])
                        r['learning_trace_bytes'] = 0
                        r['learning_state_bytes'] = lm.state_bytes
                        r['predicted_fp'] = info['predicted_fp']
                        r['passed_segments'] = info['passed_segments']
                        info = {k: v for k, v in info.items() if k != 'grid'} | dict(
                            seg_measured=seg_fp.tolist(), seg_static_fp_queries=seg_static.tolist(), hits=hits,
                            grid_top=sorted(info['grid'], key=lambda g: g['predicted_fp'])[:10])
                        sel['ra'][method] = info
                    rows.append(r)
                details.append(sel)
                E.save(dest, dict(rows=rows, selections=details, completed=False, queries=queries, seeds=seeds,
                                  protocol='round2 protocol; RA-PLBF variants added'))
                fps = {r['method']: r['fp_tail'] for r in rows if r['workload'] == name and r['seed'] == seed}
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter()-start:.1f}s '
                      + ' '.join(f'{k}={v}' for k, v in fps.items()), flush=True)
        result = json.loads(dest.read_text(encoding='utf-8'))
        result['completed'] = True
        E.save(dest, result)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        del cands
        E.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets')
    p.add_argument('--queries', type=int, default=10_000_000)
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--workloads')
    p.add_argument('--tag', default='main')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')] if a.budgets else E.BUDGETS[a.dataset],
        a.queries, a.seeds, a.workloads.split(',') if a.workloads else None, a.tag)
