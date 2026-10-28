"""实验 9：误报流偏斜度 s_F、只增不减的在线控制器、敏感性，以及 Caida 流级真实轨迹。

运行时可测的量（都只来自误报反馈，开销计入预算）：
  N_eff  HLL（2KB）统计查过的不同负 key
  D_F    HLL（2KB）统计误报过的不同 key（每个误报 key 第一次出现一定误报，所以等于不同的“基础误报”key 数）
  Q_F    计数器：误报次数 + 缓存挡下的次数（= 没有缓存时会误报的次数）
误报流模型：误报流是 W = p·N_eff 个 key 上的 Zipf(s_F)，长度 Q_F；由 (W, Q_F, D_F) 反推 s_F
（备选：Space-Saving 256 个计数器测前 256 个误报 key 的查询占比的下界，反推 s_F）。
对候选比例 f：新增的误报只来自新改成放行/变差的分段，按“一般”查询率加性计入：
  W(f) = W + N_eff·(p(f) − p)，Q_F(f) = Q_F + Q·(p(f) − p)
（均匀/Zipf 负载下 Q_F ≈ Q·p，加性与按比例缩放一致；误报高度集中时，按比例缩放会把热点的量也放大，选出过小的缓存）。
缓存按 Che-LRU 算未命中数，取最小者。

静态版（带后见之明）：用整条轨迹上测得的量选一次比例。
在线版（只增不减）：初始缓存为 0（只留草图的 4KB + Space-Saving 表）；检查点前密后疏（Q/4096 起按 2 倍递增，
之后每 Q/20），用到目前为止的测量重算比例，只升不降。测量只用前缀里自洽的一对量（前缀的 Q_F 与前缀的 W，
不向生命周期外推）：偏小由后续检查点补上，偏大则收不回来。s_F 用在线 Space-Saving 的下界反推。
升的时候按“每腾出 1 bit 增加的估计 FPR”从小到大把 backup 分段改成直接放行，腾出的内存全给缓存，不重建。

用法：python src/exp9_fp_stream_controller.py [--seeds 2]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd
from numba import njit

import common as C
from exp2_repetition_cache import QUERIES, make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp7_cache_size_rule import val_entry_bits
from exp8_cap_and_neff import S_RANGE, FastEst, model_fp, zipf_bins


SETTINGS = {"cod": (256, 1024), "caida": (128, 256, 1024), "shalla": (256, 1024, 2048),
            "caida_flow": (48, 64, 128), "mawi2020_flow": (40, 48, 64), "mawi2021_flow": (40, 48, 64)}
HLL_P = 10                                              # 1024 个寄存器（1 字节），误差约 3%
SS_K = 256
SKETCH_BYTES = 2 * (1 << HLL_P) + 8 + SS_K * 12         # 两个 HLL + 计数器 + Space-Saving 表（4B 指纹、4B 计数、4B 误差）
FINE = (0.001, 0.002, 0.005, 0.015)                     # 0–2% 之间加密的网格点
F_MODEL = np.round(np.concatenate([[0.0], FINE, [0.01, 0.02], np.arange(0.03, 0.8001, 0.01)]), 4)
PHASES = 20


def checkpoints(q):
    pts = {int(q / 2 ** k) for k in range(12, 0, -1)} | {int(q * j / PHASES) for j in range(1, PHASES)}
    return sorted(p for p in pts if 0 < p < q) + [q]


# ---------------------------------------------------------------- 草图
@njit(cache=True)
def hll_add(regs, h, p):
    idx = np.int64(h >> np.uint64(64 - p))
    w = (h << np.uint64(p)) >> np.uint64(p)
    rank = 64 - p + 1
    if w != 0:
        rank = 64 - p - (64 - C.common_prefix_bits(w, np.uint64(0))) + 1
    if rank > regs[idx]:
        regs[idx] = rank


def hll_count(regs):
    m = regs.size
    alpha = 0.7213 / (1 + 1.079 / m)
    est = alpha * m * m / np.sum(2.0 ** -regs)
    zeros = int((regs == 0).sum())
    if est <= 2.5 * m and zeros:
        est = m * np.log(m / zeros)
    return est


@njit(cache=True)
def space_saving_top_mass(keys, k):
    """Space-Saving：返回表内“计数 − 误差”之和 ÷ 总数（前 k 个 key 查询占比的下界）。"""
    tk = np.full(k, -1, np.int64)
    tc = np.zeros(k, np.int64)
    te = np.zeros(k, np.int64)
    for x in keys:
        hit = -1
        mn = 0
        for j in range(k):
            if tk[j] == x:
                hit = j
                break
            if tc[j] < tc[mn]:
                mn = j
        if hit >= 0:
            tc[hit] += 1
        else:
            te[mn] = tc[mn]
            tk[mn] = x
            tc[mn] += 1
    return (tc - te).sum() / max(1, keys.size)             # 保证的下界


# ---------------------------------------------------------------- 误报流模型
def fast_bins(n, s):
    """不做头部精确求和的快速分箱，只用于反推 s_F。"""
    edges = np.unique(np.concatenate([[1], np.round(np.logspace(0, np.log10(n + 1), 800)).astype(np.int64), [n + 1]]))
    counts = np.diff(edges).astype(np.float64)
    a, b = edges[:-1] - 0.5, edges[1:] - 0.5
    mass = counts.copy() if s == 0 else (np.log(b / a) if s == 1 else (b ** (1 - s) - a ** (1 - s)) / (1 - s))
    return counts, mass / mass.sum() / counts


def solve_s_distinct(W, QF, DF):
    W = max(int(round(W)), 2)
    def dist(s):
        c, q = fast_bins(W, s)
        return (c * (1 - np.exp(-QF * q))).sum()
    if DF >= dist(0.0):
        return 0.0
    if DF <= dist(3.0):
        return 3.0
    lo, hi = 0.0, 3.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if dist(mid) > DF else (lo, mid)
    return (lo + hi) / 2


def solve_s_topmass(W, mass):
    W = max(int(round(W)), SS_K + 1)
    def top(s):
        head = (np.arange(1, SS_K + 1, dtype=np.float64) ** -s).sum()
        c, q = fast_bins(W, s)
        total = (c * q).sum()                           # = 1，按头部精确值修正
        a = SS_K + 0.5
        tail = (W + 0.5) - a if s == 0 else (np.log((W + 0.5) / a) if s == 1 else ((W + 0.5) ** (1 - s) - a ** (1 - s)) / (1 - s))
        return head / (head + tail) / total
    if mass <= top(0.0):
        return 0.0
    if mass >= top(3.0):
        return 3.0
    lo, hi = 0.0, 3.0
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if top(mid) < mass else (lo, mid)
    return (lo + hi) / 2


def solve_W(QF, DF, s):
    """给定 s，求 W ≥ D_F 使“Zipf(s) 在 W 个 key 上抽 Q_F 次”的期望不同数等于 D_F。"""
    if QF <= 0:
        return 1.0
    DF = min(DF, QF)
    def dist(W):
        c, q = fast_bins(max(int(W), 2), s)
        return (c * (1 - np.exp(-QF * q))).sum()
    lo, hi = max(DF, 2.0), 1e10
    if dist(hi) <= DF:
        return hi
    for _ in range(40):
        mid = np.sqrt(lo * hi)
        lo, hi = (mid, hi) if dist(mid) < DF else (lo, mid)
    return np.sqrt(lo * hi)


def fit_stream(QF, DF, topmass):
    """由 (Q_F, D_F, 前 256 个误报 key 的查询占比下界) 交替拟合 (W, s_F)。
    不同误报 key 少于表长时，头部占比恒为 1、不含信息，取 s=0。"""
    if DF <= SS_K:
        return solve_W(QF, DF, 0.0), 0.0
    s, W = 0.0, max(DF, 2.0)
    for _ in range(4):
        W = solve_W(QF, DF, s)
        s = solve_s_topmass(W, topmass)
    return solve_W(QF, DF, s), s


class BinMemo:
    def __init__(self):
        self.memo = {}

    def __call__(self, W, s):
        key = (int(np.ceil(4 * np.log2(max(W, 2)))), round(s, 2))
        if key not in self.memo:
            self.memo[key] = zipf_bins(int(2 ** (key[0] / 4)), key[1])
        return self.memo[key]


def fp_stream_misses(W, s, QF, k, bins):
    if W < 1 or QF <= 0:
        return 0.0
    return model_fp(1.0, k, *bins(W, s), QF)[1]


def pick_static(est, kib, bbar, W0, QF0, s, bins, n_eff, Q):
    """W0、QF0 是基础 PLBF（比例≈草图预留）下测得的量；新增误报按加性计入。"""
    reserve = SKETCH_BYTES / (kib * 1024)
    p0 = est(kib, reserve)
    best, best_f = np.inf, reserve
    for f in F_MODEL:
        f = max(f, reserve)
        if kib * 1024 * (1 - f) <= C.N_TREES * C.TREE_BYTES:
            continue
        dp = est(kib, f) - p0
        m = fp_stream_misses(W0 + n_eff * dp, s, QF0 + Q * dp, (f - reserve) * kib * 1024 * 8 / bbar, bins)
        if m < best:
            best, best_f = m, f
    return round(best_f, 4)


# ---------------------------------------------------------------- 在线控制器
@njit(cache=True)
def ss_add(tk, tc, te, x):
    k = tk.size
    mn = 0
    for j in range(k):
        if tk[j] == x:
            tc[j] += 1
            return
        if tc[j] < tc[mn]:
            mn = j
    te[mn] = tc[mn]
    tk[mn] = x
    tc[mn] += 1


@njit(cache=True)
def lru_phase(stream, fp_static, cost, cap, h1q, in_cache, prv, nx, meta, regs_neg, regs_fp, p, tk, tc, te):
    """一段查询；meta = [head, tail, used]。返回 [误报, 缓存命中（都是基础误报 key）]。"""
    head, tail, used = meta[0], meta[1], meta[2]
    fp = 0
    hits = 0
    for t in range(stream.size):
        x = stream[t]
        hll_add(regs_neg, h1q[x], p)
        if not fp_static[x]:
            continue
        ss_add(tk, tc, te, x)
        if in_cache[x]:
            hits += 1
            if x != tail:
                a, b = prv[x], nx[x]
                if a >= 0:
                    nx[a] = b
                else:
                    head = b
                prv[b] = a
                prv[x] = tail
                nx[x] = -1
                nx[tail] = x
                tail = x
            continue
        fp += 1
        hll_add(regs_fp, h1q[x], p)
        c = cost[x]
        if cap <= 0 or c == 0 or c > cap:
            continue
        in_cache[x] = 1
        used += c
        prv[x] = tail
        nx[x] = -1
        if tail >= 0:
            nx[tail] = x
        else:
            head = x
        tail = x
        while used > cap:
            y = head
            head = nx[y]
            if head >= 0:
                prv[head] = -1
            else:
                tail = -1
            in_cache[y] = 0
            used -= cost[y]
    meta[0], meta[1], meta[2] = head, tail, used
    return np.array([fp, hits], np.int64)


def region_fpr(kind, param):
    return np.where(kind == C.BF, C.bf_fpr(np.maximum(param, 0.25)), np.where(kind == C.PASS, 1.0, 0.0))


def run_controller(setup, est, kib, stream, bbar, bins, base, tail_from=None, damp=False, thresh=0.0, init_cap=0):
    """base：预算扣掉草图后分配好的 PLBF（cache_frac = 草图占比，但缓存容量从 0 开始）。
    tail_from 给定时，返回的 FPR 只统计第 tail_from 条之后的查询（前面当预热）。
    damp：每次只走到目标增量的一半（按腾出的位数）；thresh：预测误报至少下降这个比例才增加。
    init_cap：初始缓存容量（bit）。从离线结果出发时，base 应按该缓存比例分配，init_cap = base.cache_bits − 草图位数。"""
    n_pool = setup.q_score.size
    kind = base.kind.copy()
    param = base.param.astype(np.float64)
    bits = np.where(kind == C.BF, base.m, 0).astype(np.float64)
    fp_static = base.in_pass_q | base.bf_fp_q
    reg_q = base.reg_q
    in_cache = np.zeros(n_pool, np.uint8)
    prv = np.full(n_pool, -1, np.int64)
    nx = np.full(n_pool, -1, np.int64)
    meta = np.array([-1, -1, 0], np.int64)
    regs_neg = np.zeros(1 << HLL_P, np.int64)
    regs_fp = np.zeros(1 << HLL_P, np.int64)
    tk = np.full(SS_K, -1, np.int64)
    tc = np.zeros(SS_K, np.int64)
    te = np.zeros(SS_K, np.int64)
    cap = int(init_cap)
    fp_total = hits_total = 0
    reserve = SKETCH_BYTES / (kib * 1024)
    budget_bits = kib * 1024 * 8
    start = 0
    fp_tail = 0
    cps = checkpoints(stream.size)
    if tail_from:
        cps = sorted(set(cps) | {tail_from})
    for seen in cps:
        r = lru_phase(stream[start:seen], fp_static, setup.cache_cost, cap, setup.h1q, in_cache, prv, nx, meta,
                      regs_neg, regs_fp, HLL_P, tk, tc, te)
        if tail_from is not None and start >= tail_from:
            fp_tail += int(r[0])
        start = seen
        fp_total += int(r[0])
        hits_total += int(r[1])
        if seen >= stream.size:
            break
        # 用到目前为止、前缀里自洽的一对量重算比例
        p_cur = float((est.h * region_fpr(kind, param))[est.n > 0].sum())
        n_eff = hll_count(regs_neg)
        QF_obs = fp_total + hits_total
        if QF_obs == 0:
            continue
        D_F = hll_count(regs_fp)
        W, s_F = fit_stream(QF_obs, D_F, (tc - te).sum() / QF_obs)
        n_eff = max(n_eff, W / max(p_cur, 1e-12))
        fr = region_fpr(kind, param)
        cost_r = np.where(bits > 0, est.h * (1 - fr) / np.maximum(bits, 1), np.inf)
        order = [g for g in np.argsort(cost_r) if np.isfinite(cost_r[g])]
        cand = [(0, 0.0, p_cur)]
        freed, p_path, k2 = 0.0, p_cur, 0
        for j, g in enumerate(order, start=1):
            freed += bits[g]
            p_path += est.h[g] * (1 - fr[g])
            if j % max(1, len(order) // 30) == 0 or j == len(order):
                cand.append((j, freed, p_path))
        best_j, best_m, m_stay = 0, np.inf, None
        freed_at = {}
        for j, fd, pj in cand:
            if (cap + fd) / budget_bits + reserve > 0.8:
                break
            dp = pj - p_cur
            m = fp_stream_misses(W + n_eff * dp, s_F, QF_obs + seen * dp, (cap + fd) / bbar, bins)
            freed_at[j] = fd
            if j == 0:
                m_stay = m
            if m < best_m:
                best_m, best_j = m, j
        if best_j and thresh and m_stay is not None and best_m > (1 - thresh) * m_stay:
            best_j = 0                                  # 预测收益不够大，不动
        if best_j and damp:                             # 只走一半：腾出的位数不超过目标的一半
            half = freed_at[best_j] / 2
            best_j = max((j for j, fd in freed_at.items() if 0 < j and fd <= half),
                         default=min(j for j in freed_at if j > 0))   # 最小一步都超过一半时，就走最小一步
        for g in order[:best_j]:                       # 只增不减：把这些分段改成直接放行
            kind[g] = C.PASS
            cap += int(bits[g])
            bits[g] = 0
            fp_static |= reg_q == g
    f_final = cap / budget_bits + reserve
    p_final = float((est.h * region_fpr(kind, param))[est.n > 0].sum())
    if tail_from is not None:
        return fp_tail / (stream.size - tail_from), f_final, p_final / est(kib, f_final)
    return fp_total / stream.size, f_final, p_final / est(kib, f_final)


# ---------------------------------------------------------------- 主流程
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=2)
    args = ap.parse_args()
    out = C.RESULTS / "exp9_fp_stream_controller"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, picks = [], []
    dummy = np.zeros(1, np.int64)
    for ds, budgets in SETTINGS.items():
        setup = C.Setup(ds)
        est = FastEst(setup)
        bbar = val_entry_bits(setup)
        bins = BinMemo()
        n_pool = setup.q_score.size
        order = np.argsort(setup.q_score, kind="stable")
        if ds.endswith("_flow"):
            wls = [("真实轨迹", None)]
        else:
            pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                     "全部": None}
            wls = [(w[0], w[3]) for w in workloads(pools) if w[1] != "probe-replay"]
        built, bases = {}, {}

        def structure(kib, f):
            if (kib, f) not in built:
                s = C.Structure(f"PLBF+缓存{f:.2%}", "bf", True, kib * 1024, setup, f)
                s.fp_static = s.in_pass_q | s.bf_fp_q
                built[(kib, f)] = s
            return built[(kib, f)]

        for kib in budgets:
            bases[kib] = structure(kib, round(SKETCH_BYTES / (kib * 1024), 6))
        seeds = 1 if ds.endswith("_flow") else args.seeds
        for name, spec in wls:
            for seed in range(seeds):
                stream = (C.load_flow_trace(setup) if spec is None
                          else make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order))
                q = stream.size
                # 静态（后见之明）测量：基础 PLBF 的误报流
                for kib in budgets:
                    b = bases[kib]
                    neg_regs = np.zeros(1 << HLL_P, np.int64)
                    fp_regs = np.zeros(1 << HLL_P, np.int64)   # 与在线版同样精度
                    fstream = stream[b.fp_static[stream]]
                    hll_fill(neg_regs, setup.h1q[stream])
                    hll_fill(fp_regs, setup.h1q[fstream])
                    n_eff, D_F, QF = hll_count(neg_regs), hll_count(fp_regs), fstream.size
                    p0 = est(kib, round(SKETCH_BYTES / (kib * 1024), 6))
                    W_naive = p0 * n_eff
                    s_d = solve_s_distinct(W_naive, QF, D_F) if QF else 0.0
                    top = space_saving_top_mass(fstream, SS_K) if QF else 0.0
                    W, s_ss = fit_stream(QF, D_F, top) if QF else (1.0, 0.0)
                    n_u = max(n_eff, W / max(p0, 1e-12))
                    c = {"误报流模型(W=p·N_eff, s 由不同数反推)": pick_static(est, kib, bbar, W_naive, QF, s_d, bins, n_eff, q),
                         "误报流模型(W,s 由 Q_F,D_F,头部占比拟合)": pick_static(est, kib, bbar, W, QF, s_ss, bins, n_u, q)}
                    if kib * 1024 * 0.6 > C.N_TREES * C.TREE_BYTES:
                        c["固定40%"] = 0.40
                    for f in (0.0, *FINE, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6):
                        if kib * 1024 * (1 - f) > C.N_TREES * C.TREE_BYTES:
                            c[f"网格{f:.1%}"] = f
                    picks.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                  "n_eff": n_eff, "D_F": D_F, "Q_F": QF, "W_naive": W_naive, "W_fit": W,
                                  "s_distinct": s_d, "s_ss": s_ss, "top256": top,
                                  **{k: v for k, v in c.items() if not k.startswith("网格")}})
                    for pk, f in c.items():
                        s = structure(kib, f)
                        res = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                              np.zeros(1, np.bool_))
                        rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                     "pick": pk, "frac": f, "fpr": int(res[0]) / q})
                    fpr, f_fin, drop_loss = run_controller(setup, est, kib, stream, bbar, bins, bases[kib])
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                 "pick": "在线控制器(只增不减)", "frac": f_fin, "fpr": fpr, "drop_loss": drop_loss})
            print(f"{ds} {name} done at {time.time() - t0:.1f}s")
    df = pd.DataFrame(rows)
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    pd.DataFrame(picks).to_json(out / "picks.json", orient="records", force_ascii=False, indent=1)
    report(df, pd.DataFrame(picks), out)
    print(f"total {time.time() - t0:.1f}s")


@njit(cache=True)
def hll_fill(regs, hs):
    for h in hs:
        hll_add(regs, h, HLL_P)


def report(df, picks, out):
    a = df.groupby(["dataset", "budget_kib", "workload", "pick"]).agg(fpr=("fpr", "mean"), frac=("frac", "mean"))
    best = a.fpr.groupby(level=[0, 1, 2]).transform("min")
    rel = np.where(best > 0, a.fpr / best.where(best > 0, 1), np.where(a.fpr > 0, np.inf, 1.0))
    t = pd.DataFrame({"rel": rel, "abs": (a.fpr - best) * 1e6, "frac": a.frac}).reset_index()
    methods = ["误报流模型(W=p·N_eff, s 由不同数反推)", "误报流模型(W,s 由 Q_F,D_F,头部占比拟合)",
               "在线控制器(只增不减)", "固定40%"]
    lines = ["# 实验 9：误报流偏斜度、只增不减控制器与真实轨迹", "",
             "代价相对“本实验所有候选（网格含 0–2% 加密点）里该负载最好的那个”。合成负载 2 个种子，真实轨迹 1 次。", "",
             "| 数据集 | 预算 | 方法 | 最坏相对（负载） | 相对中位数 | 最坏绝对（/百万） | 比例中位数 |",
             "|---|---:|---|---|---:|---:|---:|"]
    for (ds, kib), g in t.groupby(["dataset", "budget_kib"], sort=False):
        for m in methods:
            h = g[g.pick == m]
            if h.empty:
                continue
            w = h.loc[h.rel.idxmax()]
            lines.append(f"| {ds} | {kib}KiB | {m} | {w.rel:.2f}×（{w.workload}） | {h.rel.median():.2f}× | "
                         f"{h['abs'].max():,.0f} | {h.frac.median():.2%} |")
    drift = t[(t.workload == "向难负例漂移") & t.pick.isin(methods)]
    lines += ["", "## 难负例漂移（实验 8b 的痛点）", "", "| 数据集 | 预算 | 方法 | 相对代价 | 比例 |", "|---|---:|---|---:|---:|"]
    for _, r in drift.iterrows():
        lines.append(f"| {r.dataset} | {r.budget_kib}KiB | {r.pick} | {r.rel:.2f}× | {r.frac:.1%} |")
    ctl = df[df.pick == "在线控制器(只增不减)"]
    lines += ["", f"控制器最终配置相对“同等缓存比例重新分配”的估计 FPR 比：中位数 {ctl.drop_loss.median():.3f}，"
                  f"最大 {ctl.drop_loss.max():.3f}。",
              "", "## 拟合出的误报流参数（中位数）", "",
              "| 数据集 | 负载族 | s_F（不同数反推） | s_F（拟合） | W 拟合 ÷ p·N_eff | Q_F ÷ D_F |", "|---|---|---:|---:|---:|---:|"]
    p = picks.assign(fam=picks.workload.str.split("-").str[0])
    for (ds, fam), g in p.groupby(["dataset", "fam"], sort=False):
        lines.append(f"| {ds} | {fam} | {g.s_distinct.median():.2f} | {g.s_ss.median():.2f} | "
                     f"{(g.W_fit / g.W_naive).median():.2f} | {(g.Q_F / g.D_F.clip(lower=1)).median():.1f} |")
    t.to_json(out / "summary.json", orient="records", force_ascii=False, indent=1)
    (out / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
