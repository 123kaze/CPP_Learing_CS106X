"""Round-4 RA-PLBF variants on the round-3 streams (same protocol, cold tail).

Baselines (Gama, LearnGrid, StreamModel, Fixed48Grid) are deterministic and identical to the
round-3 rows on the same streams, so they are not recomputed here; report4.py reads them from
round3_ra_plbf/results/<round3 tag>.  Checkpointed after every (workload, seed).
"""
import argparse
import json
import time
import numpy as np
import ra4 as RA

E, C = RA.E, RA.C
Cfg = RA.Config
VARIANTS = {
    'RA4': Cfg(new_mix=0.0),
    'RA4-mix0.5': Cfg(new_mix=0.5),
    'RA4-mix1': Cfg(new_mix=1.0),
    'RA4-noSA': Cfg(new_mix=0.0, setassoc=False),
    'RA4-noGT': Cfg(new_mix=0.0, gt=False),
    'RA4-noRepeat': Cfg(new_mix=0.0, mode='norepeat'),
    'RA4-Table': Cfg(new_mix=0.0, formula='table', setassoc=False),
}
GUARDED = 'RA4'          # RA4+G = guard around this variant (add-on, not the main result)


def run(ds, budgets, queries, seeds, only=None, tag='main', names=None):
    setup, scores, safe = E.load(ds)
    out = RA.ROOT / 'results' / tag / ds
    out.mkdir(parents=True, exist_ok=True)
    E.F.simulate(np.zeros(0, np.int64), setup.h1q, safe, np.zeros(len(setup.h1q), np.bool_), 4096)
    specs = [('真实轨迹', None, 'trace')] if ds.endswith('_flow') else E.workload_specs(len(setup.h1q))
    if only:
        specs = [w for w in specs if w[0] in only]
    seeds = 1 if ds.endswith('_flow') else seeds
    names = names or list(VARIANTS)
    for kib in budgets:
        dest = out / f'{kib}.json'
        prev = json.loads(dest.read_text(encoding='utf-8')) if dest.exists() else dict(rows=[], selections=[], completed=False)
        if prev['completed']:
            continue
        rows, details = prev['rows'], prev['selections']
        done = {(r['workload'], r['seed']) for r in details}
        zeros = [c for c in (E.build(setup, scores, t, kib, 0.) for t in E.R.GAMA_TREES) if c]
        gama = min(zeros, key=lambda c: (c['structure'].est_fpr, c['trees']))
        for name, spec, family in specs:
            for seed in range(seeds):
                if (name, seed) in done:
                    continue
                start = time.perf_counter()
                stream = E.stream_for(setup, name, spec, family, seed, queries, gama['structure'])
                learn_n = len(stream) // 4
                learn, tail = stream[:learn_n], stream[learn_n:]
                frequencies = np.bincount(tail, minlength=len(setup.h1q))
                lms = {}
                sel = dict(dataset=ds, budget_kib=kib, workload=name, seed=seed, queries=len(stream),
                           learning_queries=learn_n, ra={})
                methods = []
                for vname in names:
                    cfg = VARIANTS[vname]
                    ts = time.perf_counter()
                    if cfg.gt not in lms:
                        lms[cfg.gt] = RA.summarize(learn, cfg.gt)
                    c, info = RA.select(setup, scores, lms[cfg.gt], kib, len(tail), bins=E.BinMemo(), cfg=cfg)
                    info['selection_seconds'] = time.perf_counter() - ts
                    methods.append((vname, c, info))
                    if vname == GUARDED:
                        chosen, guard = RA.guarded(setup, scores, safe, learn, kib, len(tail), gama, c, cfg=cfg)
                        sel['guard'] = guard
                        methods.append((GUARDED + '+G', chosen, dict(selection_seconds=info['selection_seconds'] + guard['guard_seconds'],
                                                                     guard=True)))
                for vname, c, info in methods:
                    result = E.evaluate(c, tail, setup, safe, frequencies)
                    r = E.row(c, result, ds, kib, name, seed, vname, len(stream), learn_n, info['selection_seconds'])
                    r['learning_state_bytes'] = lms[True].state_bytes
                    if not info.get('guard'):
                        seg_fp, seg_static, hits = RA.measure_segments(c, tail, setup, safe)
                        assert int(seg_fp.sum()) == result['fp'], (vname, seg_fp.sum(), result['fp'])
                        r['predicted_fp'] = info['predicted_fp']
                        r['predicted_fp_setassoc'] = info['predicted_fp_setassoc']
                        r['predicted_fp_fullassoc'] = info['predicted_fp_fullassoc']
                        sel['ra'][vname] = {k: v for k, v in info.items() if k != 'grid'} | dict(
                            seg_measured=seg_fp.tolist(), seg_static_fp_queries=seg_static.tolist(), hits=hits,
                            grid_top=sorted(info['grid'], key=lambda g: g['predicted_fp'])[:10])
                    else:
                        r['guard_kept_ra'] = sel['guard']['kept_ra']
                    rows.append(r)
                details.append(sel)
                E.save(dest, dict(rows=rows, selections=details, completed=False, queries=queries, seeds=seeds,
                                  variants={k: v.as_dict() for k, v in VARIANTS.items()}))
                fps = {r['method']: r['fp_tail'] for r in rows if r['workload'] == name and r['seed'] == seed}
                print(f'{ds} {kib}KiB {name} s{seed} {time.perf_counter()-start:.1f}s '
                      + ' '.join(f'{k}={v}' for k, v in fps.items()), flush=True)
        result = json.loads(dest.read_text(encoding='utf-8'))
        result['completed'] = True
        E.save(dest, result)
        print(f'COMPLETE {ds}/{kib}', flush=True)
        E.R._GSETUPS.clear()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--dataset', required=True)
    p.add_argument('--budgets', required=True)
    p.add_argument('--queries', type=int, default=10_000_000)
    p.add_argument('--seeds', type=int, default=5)
    p.add_argument('--workloads')
    p.add_argument('--tag', default='main')
    a = p.parse_args()
    run(a.dataset, [int(x) for x in a.budgets.split(',')], a.queries, a.seeds,
        a.workloads.split(',') if a.workloads else None, a.tag)
