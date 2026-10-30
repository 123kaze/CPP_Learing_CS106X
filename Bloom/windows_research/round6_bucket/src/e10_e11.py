"""E10 sensitivity (learning-period share, cache prefix bits, ways) and E11 drift.

All variants patch module-level constants of the frozen round-5/6 code at run time (engine5.PREFIX,
engine5.WAYS, ra6.WAYS, ra4.WAYS) and never edit files; the frozen setting (25%, 40 bits, 4 ways)
is one of the grid points and must reproduce the main-table rows exactly (asserted).

E10 settings (seed 0; 4 representative cases):
  caida_flow 24KiB real trace; caida 256KiB zipf1.0-全部; COD 256KiB zipf1.0-10万;
  URL 128KiB 全新对抗 (no repeats).
  learning share in {5, 10, 25, 50}% with a FIXED evaluation segment = last 50% of the stream
  (queries between the learning prefix and the evaluation segment are ignored);
  prefix bits in {24, 32, 40, 48}; ways in {1, 2, 4, 8} (25% learning, normal tail).
  Methods: Gama, LearnGrid, RA6.  Zero false negatives are re-checked for every cache variant.
E11 drift (seed 0):
  (a) cross-day: learn on the first 25% of MAWI 2021 and evaluate on the last 75% of MAWI 2022
      is impossible key-wise (different key spaces), so it is done within one trace: learn on the
      first 25%, evaluate on the last 25% of the trace only (largest time gap);
  (b) synthetic hot-set swap: Zipf 1.0 on a 100k pool of Caida; halfway through the evaluation
      segment the hot ranks are re-mapped to a disjoint random set of pool keys.
  Reported: tail FP of Gama / LearnGrid / RA6 and the FP in each quarter of the evaluation part.
usage: e10_e11.py e10 | e11
"""
import os
for _v in ('NUMBA_NUM_THREADS', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS'):
    os.environ[_v] = '1'
import csv  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402
import numpy as np  # noqa: E402
import ra6  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R5 = ROOT.parent / 'round5_dp' / 'results'
E5, RA = ra6.E5, ra6.RA
K = E5.K
CASES = (('caida_flow', 24, '真实轨迹'), ('caida', 256, 'zipf1.0-全部'), ('cod', 256, 'zipf1.0-10万'), ('url', 128, '全新对抗'))


_BUCKETS_OF = ra6.buckets_of


def set_cache(prefix, ways):
    """Patch the frozen modules' constants (no file is edited). ra6.buckets_of binds its prefix
    as a default argument, so it is wrapped to read the current prefix."""
    E5.PREFIX, E5.WAYS = prefix, ways
    ra6.WAYS = ways
    RA.ra4.WAYS = ways
    ra6.buckets_of = lambda h, B, P=None: _BUCKETS_OF(h, B, prefix if P is None else P)


def run_methods(setup, scores, safe, kib, learn, tail):
    cands = E5.candidates(setup, scores, kib)
    gama = E5.gama(cands)
    grid, _ = E5.replay_best(cands, learn, setup, safe)
    lm = RA.ra4.summarize(learn, True)
    ra, _ = ra6.select6(setup, scores, lm, kib, len(tail))
    out = {}
    for name, c in (('Gama', gama), ('LearnGrid', grid), ('RA6', ra)):
        r = E5.evaluate(c, tail, setup, safe)
        out[name] = dict(fp=int(r['fp']), trees=int(c['trees']), cache_bytes=int(c['cache_bytes']))
        if c['cache_bytes']:
            spec = K.layout(c['cache_bytes'], E5.PREFIX, E5.WAYS)
            data = K.allocate(spec)
            K.replay(np.asarray(tail, np.int64), setup.h1q, safe, c['structure'].fp_static, data, spec['buckets'], E5.PREFIX,
                     spec['Q'], spec['ob'], spec['slot_bits'], E5.WAYS, spec['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
            assert K.count_member_hits(data, setup.h1m, spec['buckets'], E5.PREFIX, spec['Q'], spec['ob'], spec['slot_bits'], E5.WAYS) == 0
    return out


def main_row(ds, kib, wl, method):
    f = (R5 if method != 'RA6' else ROOT / 'results' / 'main') / f'rows_{ds}_{kib}.csv'
    for r in csv.DictReader(open(f, encoding='utf-8')):
        if r['workload'] == wl and r['seed'] == '0' and r['method'] == method:
            return int(r['fp_tail'])


def e10():
    res = []
    for ds, kib, wl in CASES:
        setup, scores, safe = E5.load(ds)
        spec = None if ds.endswith('_flow') else dict(E5.workload_specs(len(setup.h1q)))[wl]
        base = E5.base_stream(setup, wl, spec, 0)
        N = len(base)
        # learning share with a fixed evaluation segment (last 50%)
        set_cache(40, 4)
        for share in (.05, .10, .25, .50):
            learn, tail = base[:int(N * share)], base[N // 2:]
            out = run_methods(setup, scores, safe, kib, learn, tail)
            res.append(dict(case=f'{ds} {kib} {wl}', variable='learning_share', value=share, **out))
            print(ds, kib, wl, 'share', share, {k: v['fp'] for k, v in out.items()}, flush=True)
        n = N // 4
        for prefix in (24, 32, 40, 48):
            set_cache(prefix, 4)
            out = run_methods(setup, scores, safe, kib, base[:n], base[n:])
            res.append(dict(case=f'{ds} {kib} {wl}', variable='prefix_bits', value=prefix, **out))
            print(ds, kib, wl, 'prefix', prefix, {k: v['fp'] for k, v in out.items()}, flush=True)
            if prefix == 40:
                for m in out:
                    ref = main_row(ds, kib, wl, m)
                    assert ref is None or ref == out[m]['fp'], ('frozen setting not reproduced', m, ref, out[m]['fp'])
        for ways in (1, 2, 4, 8):
            set_cache(40, ways)
            out = run_methods(setup, scores, safe, kib, base[:n], base[n:])
            res.append(dict(case=f'{ds} {kib} {wl}', variable='ways', value=ways, **out))
            print(ds, kib, wl, 'ways', ways, {k: v['fp'] for k, v in out.items()}, flush=True)
        set_cache(40, 4)
        E5._TREE.clear()
        E5.R._GSETUPS.clear()
    (ROOT / 'results' / 'e10.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


def quarters(c, tail, setup, safe):
    spec = K.layout(c['cache_bytes'], E5.PREFIX, E5.WAYS) if c['cache_bytes'] else None
    fp = c['structure'].fp_static
    if spec is None:
        q = np.array_split(fp[tail], 4)
        return [int(x.sum()) for x in q]
    miss = K.simulate(tail, setup.h1q, safe, fp, c['cache_bytes'], E5.PREFIX, E5.WAYS, per_key=False)
    # per-quarter FP by replaying with a running counter
    data = K.allocate(spec)
    out = []
    for part in np.array_split(np.asarray(tail, np.int64), 4):
        r = K.replay(part, setup.h1q, safe, fp, data, spec['buckets'], E5.PREFIX, spec['Q'], spec['ob'], spec['slot_bits'],
                     E5.WAYS, spec['handbits'], 2 ** 62, np.zeros(0, np.int64), np.zeros(0, np.bool_))
        out.append(int(r[0]))
    assert sum(out) == miss['fp']
    return out


def e11():
    res = []
    set_cache(40, 4)
    for ds, kib in (('mawi2021_flow', 24), ('mawi2022_flow', 24), ('caida_flow', 24)):
        setup, scores, safe = E5.load(ds)
        base = E5.base_stream(setup, '真实轨迹', None, 0)
        N = len(base)
        learn, tail = base[:N // 4], base[3 * N // 4:]
        cands = E5.candidates(setup, scores, kib)
        gama = E5.gama(cands)
        grid, _ = E5.replay_best(cands, learn, setup, safe)
        ra, _ = ra6.select6(setup, scores, RA.ra4.summarize(learn, True), kib, len(tail))
        out = {n: dict(fp=int(E5.evaluate(c, tail, setup, safe)['fp']), quarters=quarters(c, tail, setup, safe))
               for n, c in (('Gama', gama), ('LearnGrid', grid), ('RA6', ra))}
        res.append(dict(case=f'{ds} {kib}: learn first 25%, evaluate last 25% (gap 50%)', **out))
        print(ds, {k: v['fp'] for k, v in out.items()}, flush=True)
        E5._TREE.clear()
    ds, kib = 'caida', 256
    setup, scores, safe = E5.load(ds)
    spec = ('zipf', 100_000, 1.0)
    base = E5.base_stream(setup, 'zipf1.0-10万', spec, 0)
    N = len(base)
    n = N // 4
    learn, tail = base[:n], base[n:].copy()
    rng = np.random.default_rng(11)
    pool = np.unique(base)
    others = np.setdiff1d(np.arange(len(setup.h1q)), pool)
    remap = dict(zip(pool.tolist(), rng.choice(others, len(pool), replace=False).tolist()))
    half = len(tail) // 2
    tail[half:] = np.array([remap[x] for x in tail[half:].tolist()], np.int64)
    cands = E5.candidates(setup, scores, kib)
    gama = E5.gama(cands)
    grid, _ = E5.replay_best(cands, learn, setup, safe)
    ra, _ = ra6.select6(setup, scores, RA.ra4.summarize(learn, True), kib, len(tail))
    out = {n_: dict(fp=int(E5.evaluate(c, tail, setup, safe)['fp']), quarters=quarters(c, tail, setup, safe))
           for n_, c in (('Gama', gama), ('LearnGrid', grid), ('RA6', ra))}
    res.append(dict(case='caida 256 zipf1.0-10万: hot set swapped to unseen keys halfway through evaluation', **out))
    print('swap', {k: v['fp'] for k, v in out.items()}, flush=True)
    (ROOT / 'results' / 'e11.json').write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding='utf-8')


if __name__ == '__main__':
    {'e10': e10, 'e11': e11}[sys.argv[1]]()
