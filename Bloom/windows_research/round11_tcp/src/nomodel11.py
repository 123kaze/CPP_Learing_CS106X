"""No-model control for round 11: a plain Bloom filter (t = 0 trees) plus the negative cache.

Every candidate in Gama / RA6 has at least 1 tree; when the model is useless (round 11) a plain BF
may be better.  Here, for every TCP-only setting:
  BF          one packed Bloom filter over all members, whole budget, optimal k = round(bits/n * ln 2);
  BF+cache    the same BF with each cache fraction of engine5.FRACS, chosen by replaying every candidate
              on the learning period (engine5.replay_best, exactly as LearnGrid), evaluated on the tail.
Physical accounting: BF bytes + cache bytes + the 1-tree structure's array overhead and a 1-region
metadata block (conservative: no model arrays are needed, their headers are still charged).
--cache fp64 uses the index-free fingerprint cache (round 10) instead of the member-index cache.
usage: nomodel11.py <dataset> [--cache index|fp64]   -> results/nomodel/rows_<ds>_<kib>.csv
"""
import argparse
import csv
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import tcp11 as T  # noqa: E402  (registers the TCP-only datasets)

T.register_budgets()
sys.path.insert(0, str(T.WR / 'round10_fpcache' / 'src'))
import engine5 as E5  # noqa: E402
import cache_fp  # noqa: E402

R, C = E5.R, E5.C
COLS = ['dataset', 'budget_kib', 'workload', 'seed', 'method', 'trees', 'frac', 'cache_alloc_bytes', 'bf_bytes', 'k',
        'bits_per_member', 'total_bytes', 'fp_tail', 'fpr_tail', 'static_fpr_pool', 'select_s']
META = 1 * 8 + 1 * (1 + 8 + 8) + 2 * 8                      # engine5.tree metadata formula with 1 region


def plain_bf(setup, scores, kib, frac):
    budget = kib * 1024
    cache_bytes, slots = E5.cache_alloc(budget, frac)
    fixed = E5.tree(setup, scores, 1).overhead_bytes + META
    m_bits = (budget - fixed - cache_bytes) * 8
    if m_bits <= 0:
        return None
    n = len(setup.h1m)
    bpm = m_bits / n
    k = np.array([max(1, int(np.rint(bpm * np.log(2))))], np.int64)
    m = np.array([m_bits], np.int64)
    off = np.array([0, m_bits], np.int64)
    kind = np.array([C.BF], np.uint8)
    bits = np.zeros((m_bits + 7) // 8, np.uint8)
    R.packed_build(setup.h1m, np.zeros(n, np.int32), off, m, k, bits)
    assert R.packed_query(setup.h1m, np.zeros(n, np.int32), kind, off, m, k, bits).all(), 'Bloom false negative'
    fp = R.packed_query(setup.h1q, np.zeros(len(setup.h1q), np.int32), kind, off, m, k, bits)
    used = fixed + cache_bytes + bits.nbytes
    assert used <= budget
    st = SimpleNamespace(trees=0, fp_static=fp, est_fpr=float(C.bf_fpr(bpm)), model_bytes=0, filter_bytes=bits.nbytes,
                         metadata_bytes=META, array_overhead_bytes=fixed - META, used_bytes=used, budget_bytes=budget,
                         cache_bytes=cache_bytes, k=k, bpm=bpm)
    return dict(trees=0, frac=float(frac), cache_reserved_bytes=int(budget * frac), cache_bytes=cache_bytes,
                slots=slots, structure=st)


def run(ds, tag):
    setup, scores, safe = E5.load(ds)
    out = T.ROOT / 'results' / 'nomodel'
    out.mkdir(parents=True, exist_ok=True)
    for kib in E5.BUDGETS[ds]:
        cands = [c for c in (plain_bf(setup, scores, kib, f) for f in E5.FRACS) if c is not None]
        base = E5.base_stream(setup, '真实轨迹', None, 0)
        n = len(base) // 4
        tail = base[n:]
        ts = time.perf_counter()
        best, _ = E5.replay_best(cands, base[:n], setup, safe)
        sel = time.perf_counter() - ts
        rows = []
        for name, c, s in ((f'BF{tag}', cands[0], 0.), (f'BF+缓存{tag}', best, sel)):
            assert name != f'BF{tag}' or c['frac'] == 0
            fp = E5.evaluate(c, tail, setup, safe)['fp']
            st = c['structure']
            rows.append(dict(dataset=ds, budget_kib=kib, workload='真实轨迹', seed=0, method=name, trees=0, frac=c['frac'],
                             cache_alloc_bytes=c['cache_bytes'], bf_bytes=st.filter_bytes, k=int(st.k[0]),
                             bits_per_member=round(st.bpm, 4), total_bytes=st.used_bytes, fp_tail=fp,
                             fpr_tail=fp / len(tail), static_fpr_pool=float(st.fp_static.mean()), select_s=round(s, 3)))
        dest = out / f'rows_{ds}_{kib}.csv'
        new = not dest.exists()
        with dest.open('a', encoding='utf-8', newline='') as fh:
            w = csv.DictWriter(fh, fieldnames=COLS)
            if new:
                w.writeheader()
            w.writerows(rows)
        print(ds, kib, ' '.join(f"{r['method']}={r['fp_tail']} (frac {r['frac']})" for r in rows), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('dataset')
    p.add_argument('--cache', choices=('index', 'fp64'), default='index')
    a = p.parse_args()
    if a.cache == 'fp64':
        E5.K = cache_fp
    run(a.dataset, '' if a.cache == 'index' else '-fp64')
