"""Round-5 engine: FastPLBF DP allocation (F-A), arbitrary-bucket cache (F-B), symmetric probe replay (F-C).

Physical accounting as in round 2: packed Bloom bits, executable model arrays, navigation
arrays and every ndarray header are charged; the cache is charged at its allocated bytes.
Every structure asserts zero member false negatives and used_bytes <= budget.
"""
import sys
import time
from pathlib import Path
from types import SimpleNamespace
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'round2_backlog' / 'src'))
import engine as E  # noqa: E402  (round-2 engine: datasets, streams, packed BF, model arrays)
import dp_alloc as D  # noqa: E402
import cache5 as K  # noqa: E402

R, C = E.R, E.C
TREES = R.GAMA_TREES
FRACS = (0., .001, .002, .005, .01, .015, .02, .05, .1, .2, .3, .4, .6)
PREFIX, WAYS = 40, 4
BUDGETS = {'cod': (256, 1024, 4096), 'caida': (128, 256, 1024, 2048), 'shalla': (256, 1024, 2048, 4096),
           'url': (64, 128, 256), 'caida_flow': (16, 24, 32, 256), 'mawi2020_flow': (16, 24, 32, 128),
           'mawi2021_flow': (16, 24, 32, 128), 'mawi2022_flow': (16, 24, 32, 128)}
HIGH = {'cod': 4096, 'caida': 2048, 'shalla': 4096, 'caida_flow': 256, 'mawi2020_flow': 128,
        'mawi2021_flow': 128, 'mawi2022_flow': 128}
ZIPFS = (0.8, 1.0, 1.2)
PROBE = '探测重放10%'
LN2SQ = np.log(2) ** 2
_TREE = {}


def load(ds):
    return E.load(ds)


def sig(x):
    return 1 / (1 + np.exp(-x))


def tree(setup, scores, t):
    """Per-tree segments: member counts, validation counts, smoothed h, segment of every pool key."""
    key = (setup.name, t)
    if key not in _TREE:
        gs = R.gama_setup(setup, scores[t])
        if key not in R._MODEL_ARRAYS:
            import lightgbm as lgb
            from end_to_end import model_arrays
            R._MODEL_ARRAYS[key] = model_arrays(lgb.Booster(model_file=str(C.CACHE / setup.name / 'model200.txt')), t)
        seg_m = D.segment_of(sig(gs.mem_score))
        seg_v = D.segment_of(sig(gs.val_score))
        seg_q = D.segment_of(sig(gs.q_score))
        g = np.bincount(seg_m, minlength=D.N_SEG)
        v = np.bincount(seg_v, minlength=D.N_SEG)
        arrays = R._MODEL_ARRAYS[key]
        model_bytes = sum(a.nbytes for a in arrays.values())
        k = D.K_REG
        metadata = (k + 1) * 8 + k * (1 + 8 + 8) + (k + 1) * 8   # thresholds, kind/m/k, offsets
        overhead = 12 * R._sys.getsizeof(np.empty(0, np.uint8)) + R._sys.getsizeof(arrays)
        _TREE[key] = SimpleNamespace(t=t, seg_m=seg_m, seg_q=seg_q, g=g, v=v, h=D.smoothed(v),
                                     model_bytes=model_bytes, metadata_bytes=metadata, overhead_bytes=overhead,
                                     fixed=model_bytes + metadata + overhead)
    return _TREE[key]


def cache_alloc(budget_bytes, frac):
    if frac <= 0:
        return 0, 0
    spec = K.layout(int(budget_bytes * frac), PREFIX, WAYS)
    return spec['allocated_bytes'], spec['slots']


def region_bits(td, b, f):
    """Bits per member, kind, member count per region for DP output (b bounds, f FPRs)."""
    reg_seg = D.region_of_segment(b)
    n = np.bincount(reg_seg, weights=td.g, minlength=len(f))
    bpm = np.where((f > 0) & (f < 1), np.log(1 / np.clip(f, 1e-300, 1)) / LN2SQ, 0.)
    m = np.where(n > 0, np.floor(bpm * n), 0).astype(np.int64)
    kind = np.where(n == 0, C.EMPTY, np.where(m > 0, C.BF, C.PASS)).astype(np.uint8)
    return reg_seg, n, bpm, m, kind


def build(setup, scores, t, kib, frac=0., weights=None, cache_bytes=None, slots=None):
    """DP-allocated structure; weights=None -> validation h (PLBF/Gama)."""
    td = tree(setup, scores, t)
    budget = kib * 1024
    if cache_bytes is None:
        cache_bytes, slots = cache_alloc(budget, frac)
    avail = (budget - td.fixed - cache_bytes) * 8
    if avail <= 0:
        return None
    w = td.v + 1.0 if weights is None else np.asarray(weights, np.float64)
    M = float(avail)
    for _ in range(20):                       # integer floors / smoothing can overshoot: shrink M
        b, f, e = D.allocate(td.g, w, M)
        reg_seg, n, bpm, m, kind = region_bits(td, b, f)
        if m.sum() <= avail:
            break
        M *= avail / m.sum() * 0.9999
    assert m.sum() <= avail
    k = np.where(kind == C.BF, np.maximum(1, np.rint(bpm * np.log(2))), 0).astype(np.int64)
    off = np.concatenate([[0], np.cumsum(m)]).astype(np.int64)
    bits = np.zeros((int(off[-1]) + 7) // 8, np.uint8)
    reg_m = reg_seg[td.seg_m].astype(np.int32)
    R.packed_build(setup.h1m, reg_m, off, m, k, bits)
    assert R.packed_query(setup.h1m, reg_m, kind, off, m, k, bits).all(), 'Bloom false negative'
    reg_q = reg_seg[td.seg_q].astype(np.int32)
    fp = R.packed_query(setup.h1q, reg_q, kind, off, m, k, bits)
    used = td.fixed + cache_bytes + bits.nbytes
    assert used <= budget
    reg_fpr = np.where(kind == C.PASS, 1., np.where(kind == C.BF, C.bf_fpr(np.maximum(bpm, 1e-9)), 0.))
    # Gama's criterion: DP expected FPR under the validation h (original get_fpr())
    est = float(e) if weights is None else float((td.h * reg_fpr[reg_seg]).sum())
    st = SimpleNamespace(trees=t, b=b, f=f, kind=kind, m=m, k=k, fp_static=fp, est_fpr=est,
                         seg_fpr=reg_fpr[reg_seg], seg_fpr_cont=np.where(n[reg_seg] > 0, f[reg_seg], 0.),
                         q_region=reg_q, model_bytes=td.model_bytes, metadata_bytes=td.metadata_bytes,
                         array_overhead_bytes=td.overhead_bytes, filter_bytes=bits.nbytes, used_bytes=used,
                         budget_bytes=budget, cache_bytes=cache_bytes)
    return dict(trees=t, frac=float(frac), cache_reserved_bytes=int(budget * frac), cache_bytes=cache_bytes,
                slots=slots if slots is not None else K.layout(cache_bytes)['slots'] if cache_bytes else 0,
                structure=st)


def candidates(setup, scores, kib, fracs=FRACS, trees=TREES):
    out = []
    for t in trees:
        if tree(setup, scores, t).fixed >= kib * 1024:
            continue
        for f in fracs:
            c = build(setup, scores, t, kib, f)
            if c is not None:
                out.append(c)
    return out


def gama(cands):
    zeros = [c for c in cands if c['frac'] == 0]
    return min(zeros, key=lambda c: (c['structure'].est_fpr, c['trees']))


def workload_specs(n_pool):
    pools = {'1万': min(10000, n_pool), '10万': min(100000, n_pool),
             **({'100万': 1000000} if n_pool > 1500000 else {}), '全部': None}
    out = []
    for name, size in pools.items():
        out.append((f'uniform-{name}', ('uniform', size)))
        for s in ZIPFS:
            out.append((f'zipf{s}-{name}', ('zipf', size, s)))
    out += [('每key一次', ('once',)), ('全新对抗', ('fresh',)), (PROBE, ('uniform', None))]
    return out


def base_stream(setup, name, spec, seed, queries=10_000_000):
    if spec is None:
        return C.load_flow_trace(setup)
    import exp2_repetition_cache as E2
    E2.QUERIES = queries
    return R.make_stream(spec, len(setup.h1q), np.random.default_rng(2000 + seed),
                         np.argsort(setup.q_score, kind='stable'))


def tail_for(c, name, base_tail, seed):
    """F-C: in the probe workload every structure faces replays of its own observed FPs."""
    if name != PROBE:
        return base_tail
    return E.probe_replay(base_tail, c['structure'].fp_static, 11000 + seed)


def evaluate(c, tail, setup, safe, per_key=False):
    st = c['structure']
    if c['cache_bytes'] == 0 and not per_key:
        fp = int(st.fp_static[tail].sum())
        return dict(fp=fp, hits=0, cache_hit_rate=0.0, inserts=0, evictions=0)
    r = K.simulate(tail, setup.h1q, safe, st.fp_static, c['cache_bytes'], PREFIX, WAYS, per_key=per_key)
    static = int(st.fp_static[tail].sum())
    r['cache_hit_rate'] = r['hits'] / max(1, static) if static else 0.0
    return r


def replay_best(cands, stream, setup, safe, order_key=None):
    """Exact replay of every candidate on `stream` with early stopping; returns best, all fps."""
    freq = np.bincount(stream, minlength=len(setup.h1q))
    order = sorted(cands, key=order_key or (lambda c: c['structure'].est_fpr))
    best, fps = None, {}
    for c in order:
        st = c['structure']
        lim = best[0] if best else 2 ** 62
        if c['cache_bytes'] == 0:
            fp, cut = int(freq[st.fp_static].sum()), False
        else:
            r = K.simulate(stream, setup.h1q, safe, st.fp_static, c['cache_bytes'], PREFIX, WAYS, limit=lim)
            fp, cut = r['fp'], bool(r['cutoff'])
        fps[c['trees'], c['frac']] = (fp, cut)
        if not cut:
            key = (fp, st.est_fpr, c['trees'], c['frac'])
            if best is None or key < best[:4]:
                best = key + (c,)
    return best[-1], fps


def oracle(cands, name, base_tail, seed, setup, safe):
    """E2: every candidate on the evaluation segment (its own tail under F-C), exact."""
    out = {}
    for c in cands:
        tail = tail_for(c, name, base_tail, seed)
        out[c['trees'], c['frac']] = evaluate(c, tail, setup, safe)['fp']
    return out
