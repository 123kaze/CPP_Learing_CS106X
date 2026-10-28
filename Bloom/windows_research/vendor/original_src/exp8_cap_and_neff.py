"""实验 8：缓存比例上限的模型推导，以及用 HyperLogLog 在线估计 N_eff。

第 1 部分（上限）：不看轨迹，只用模型、验证集和声明的部署参数（Zipf 指数范围 S、生命周期查询数 Q、
负例全集大小 N）。对每个比例 f：
  p(f)  = 预算扣掉缓存后的 PLBF 在验证集上的估计 FPR（与 common.Structure 同一个分配器）
  k(f)  = f · 预算 / b̄（缓存能放的条数）
  误报 key 视为在热度排名上随机抽取的 p(f) 比例，查询服从 Zipf(s)：
    TOP-k：  FP = p·[Σ_{i≤m}(1−e^{−Q q_i}) + Q·Σ_{i>m} q_i]，m = k/p（缓存最热的 k 个误报 key，首次出现仍误报）
    Che-LRU：p·Σ(1−e^{−q_i T}) = k 解出特征时间 T，FP = p·Q·Σ q_i e^{−q_i T} + 首次误报修正
  推出的比例 = argmin_f max_{s∈S} FP(f,s) / min_f' FP(f',s)。
  模型里没有任何拟合常数，所以“留一数据集”自动满足。

第 2 部分（N_eff）：HyperLogLog（2048 个寄存器，2KB，从缓存预算里扣）统计前 L 条查询中的不同负 key 数，
L ∈ {10%, 100%} × 查询总量；代入规则 f = min(p(f)·N_eff·b̄/预算, 上限)，上限取第 1 部分 Che-LRU 推出的比例。

评估：对推出的比例跑真实负载（LRU，3 个种子，与实验 7 同一批轨迹），代价相对“实验 7 与本实验所有候选比例里该负载最好的那个”。

用法：python src/exp8_cap_and_neff.py [--seeds 3]
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
from exp7_cache_size_rule import SETTINGS, val_entry_bits


S_RANGE = (0.0, 0.5, 0.8, 1.1, 1.5)
F_GRID = np.round(np.arange(0.0, 0.8001, 0.005), 4)
HLL_P = 11
HLL_BYTES = 1 << HLL_P
N_BINS = 4000


class FastEst:
    """只跑分配器，不建 BF：给出 p(f)。"""

    def __init__(self, setup):
        self.setup = setup
        reg_m = np.searchsorted(setup.cuts, setup.mem_score, side="right")
        nreg = setup.cuts.size + 1
        self.n = np.bincount(reg_m, minlength=nreg).astype(np.float64)
        cnt = np.bincount(np.searchsorted(setup.cuts, setup.val_score, side="right"), minlength=nreg)
        self.h = (cnt + 0.5) / (cnt.sum() + 0.5 * nreg)
        self.memo = {}

    def __call__(self, kib, f):
        key = (kib, round(f, 6))
        if key not in self.memo:
            budget = (kib * 1024 - C.N_TREES * C.TREE_BYTES) * 8 - int(kib * 1024 * f) * 8
            self.memo[key] = C.allocate(self.n, self.h, budget, "bf")[3] if budget > 0 else 1.0
        return self.memo[key]


def zipf_bins(n, s):
    """把 1..n 的排名按对数分箱：返回每箱的条数和箱内每个 key 的平均查询概率。"""
    edges = np.round(np.logspace(0, np.log10(n + 1), N_BINS)).astype(np.int64)
    edges = np.unique(np.concatenate([[1], edges, [n + 1]]))
    edges = edges[(edges >= 1) & (edges <= n + 1)]
    counts = np.diff(edges).astype(np.float64)
    a, b = edges[:-1] - 0.5, edges[1:] - 0.5           # Σ_{i=a}^{b-1} i^{-s} 的积分近似
    if s == 0:
        mass = counts.copy()
    elif s == 1:
        mass = np.log(b / a)
    else:
        mass = (b ** (1 - s) - a ** (1 - s)) / (1 - s)
    if s > 0:                                          # 跨度小的头部箱子精确求和，积分近似在排名 1 附近偏差大
        for j in np.flatnonzero(counts <= 1000):
            mass[j] = (np.arange(edges[j], edges[j + 1], dtype=np.float64) ** -s).sum()
    return counts, mass / mass.sum() / counts


def model_fp(p, k, counts, q, Q):
    """返回 (TOP-k 误报数, Che-LRU 误报数)。"""
    touched = 1 - np.exp(-Q * q)                      # 每个 key 在 Q 次查询里至少出现一次的概率
    if p <= 0:
        return 0.0, 0.0
    m = k / p                                          # 能缓存的“排名深度”
    cum = np.concatenate([[0], np.cumsum(counts)])
    full = np.searchsorted(cum, m, side="right") - 1   # 完全落在缓存内的箱
    frac = np.zeros(counts.size)
    frac[:full] = 1.0
    if full < counts.size:
        frac[full] = np.clip((m - cum[full]) / counts[full], 0, 1)
    topk = p * ((counts * frac * touched).sum() + Q * (counts * (1 - frac) * q).sum())
    if p * counts.sum() <= k:                          # 全部装得下：只剩首次误报
        che = p * (counts * touched).sum()
    else:
        lo, hi = 1e-3, 1e15
        for _ in range(80):
            T = np.sqrt(lo * hi)
            if p * (counts * (1 - np.exp(-q * T))).sum() > k:
                hi = T
            else:
                lo = T
        hit = 1 - np.exp(-q * T)
        che = p * (Q * (counts * q * (1 - hit)).sum() + (counts * touched * hit).sum())
    return topk, che


def robust_pick(curves):
    """curves: {s: FP 数组（对 F_GRID）}。返回最坏相对代价最小的比例及其模型代价。"""
    rel = np.array([c / max(c.min(), 1e-12) for c in curves.values()])
    worst = rel.max(axis=0)
    i = int(np.argmin(worst))
    return float(F_GRID[i]), float(worst[i])


@njit(cache=True)
def hll_registers(h, p):
    reg = np.zeros(1 << p, np.int64)
    for v in h:
        idx = np.int64(v >> np.uint64(64 - p))
        w = (v << np.uint64(p)) >> np.uint64(p)
        rank = 64 - p + 1
        if w != 0:
            rank = 64 - p - (64 - C.common_prefix_bits(w, np.uint64(0))) + 1
        if rank > reg[idx]:
            reg[idx] = rank
    return reg


def hll_estimate(h):
    m = 1 << HLL_P
    reg = hll_registers(h, HLL_P)
    alpha = 0.7213 / (1 + 1.079 / m)
    est = alpha * m * m / np.sum(2.0 ** -reg)
    zeros = int((reg == 0).sum())
    if est <= 2.5 * m and zeros:
        est = m * np.log(m / zeros)
    return est


def rule_with_n(est, kib, n_eff, bbar, cap, reserve_bytes=0):
    f = 0.0
    for _ in range(40):
        f_new = min(est(kib, f) * n_eff * bbar / (kib * 1024 * 8) + reserve_bytes / (kib * 1024), cap)
        if abs(f_new - f) < 1e-4:
            break
        f = 0.5 * f + 0.5 * f_new
    return round(max(f, reserve_bytes / (kib * 1024)), 4)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    out = C.RESULTS / "exp8_cap_and_neff"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    model_rows, pick_rows, eval_rows = [], [], []
    for ds, budgets in SETTINGS.items():
        setup = C.Setup(ds)
        est = FastEst(setup)
        bbar = val_entry_bits(setup)
        n_pool = setup.q_score.size
        order = np.argsort(setup.q_score, kind="stable")
        bins = {s: zipf_bins(n_pool, s) for s in S_RANGE}
        caps = {}
        for kib in budgets:
            feasible = F_GRID[kib * 1024 * (1 - F_GRID) > C.N_TREES * C.TREE_BYTES]
            curves = {"TOP-k": {}, "Che-LRU": {}}
            for s in S_RANGE:
                tk, ch = [], []
                for f in F_GRID:
                    if f not in feasible:
                        tk.append(np.inf)
                        ch.append(np.inf)
                        continue
                    p = est(kib, f)
                    a, b = model_fp(p, f * kib * 1024 * 8 / bbar, *bins[s], QUERIES)
                    tk.append(a)
                    ch.append(b)
                    model_rows.append({"dataset": ds, "budget_kib": kib, "s": s, "frac": float(f), "p": p,
                                       "fp_topk": a, "fp_che": b})
                curves["TOP-k"][s] = np.array(tk)
                curves["Che-LRU"][s] = np.array(ch)
            for name, cv in curves.items():
                f, w = robust_pick(cv)
                per_s = {s: float(F_GRID[int(np.argmin(c))]) for s, c in cv.items()}
                pick_rows.append({"dataset": ds, "budget_kib": kib, "model": name, "frac": f,
                                  "model_worst_rel": w, **{f"best_s{s}": v for s, v in per_s.items()}})
            caps[kib] = next(r["frac"] for r in pick_rows
                             if r["dataset"] == ds and r["budget_kib"] == kib and r["model"] == "Che-LRU")
        print(f"{ds}: model done at {time.time() - t0:.1f}s; Che caps {caps}")

        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        built = {}

        def structure(kib, f):
            if (kib, f) not in built:
                s = C.Structure(f"PLBF+缓存{f:.2%}", "bf", True, kib * 1024, setup, f)
                s.fp_static = s.in_pass_q | s.bf_fp_q
                built[(kib, f)] = s
            return built[(kib, f)]

        dummy = np.zeros(1, np.int64)
        for name, family, pool, spec, _ in [w for w in workloads(pools) if w[1] != "probe-replay"]:
            for seed in range(args.seeds):
                stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order)
                windows = {}
                for share in (0.1, 1.0):
                    L = max(1, int(stream.size * share))
                    windows[share] = (L, hll_estimate(setup.h1q[stream[:L]]), int(np.unique(stream[:L]).size))
                for kib in budgets:
                    cands = {f"模型-{r['model']}": round(r["frac"], 4) for r in pick_rows
                             if r["dataset"] == ds and r["budget_kib"] == kib}
                    for share, (L, n_eff, n_true) in windows.items():
                        f = rule_with_n(est, kib, n_eff, bbar, caps[kib], HLL_BYTES)
                        cands[f"规则+HLL(前{share:.0%})"] = f
                        eval_rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                          "kind": "n_eff", "window": share, "n_eff": n_eff,
                                          "n_true_window": n_true, "frac": f})
                    cands["规则(已知N,上限=Che)"] = rule_with_n(est, kib, n_pool, bbar, caps[kib])
                    for pick, f in cands.items():
                        s = structure(kib, f)
                        res = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                              np.zeros(1, np.bool_))
                        eval_rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                          "kind": "eval", "pick": pick, "frac": f, "fpr": int(res[0]) / stream.size})
            print(f"{ds} {name} done at {time.time() - t0:.1f}s")
    pd.DataFrame(model_rows).to_json(out / "model_curves.json", orient="records", force_ascii=False)
    pd.DataFrame(pick_rows).to_json(out / "model_picks.json", orient="records", force_ascii=False, indent=1)
    ev = pd.DataFrame(eval_rows)
    (out / "rows.json").write_text(ev.to_json(orient="records", force_ascii=False, indent=1))
    report(ev, pd.DataFrame(pick_rows), out)
    print(f"total {time.time() - t0:.1f}s")


def report(ev, picks, out):
    e7 = pd.DataFrame(json.loads((C.RESULTS / "exp7_cache_size_rule" / "rows.json").read_text()))
    e7r = pd.DataFrame(json.loads((C.RESULTS / "exp7_cache_size_rule" / "rules.json").read_text()))
    e8 = ev[ev.kind == "eval"]
    # 每个 (设置, 负载) 的“最好”取实验 7 网格/规则与本实验所有候选的并集
    pool = pd.concat([e7[["dataset", "budget_kib", "workload", "seed", "frac", "fpr"]],
                      e8[["dataset", "budget_kib", "workload", "seed", "frac", "fpr"]]])
    per = pool.groupby(["dataset", "budget_kib", "workload", "frac"]).fpr.mean()
    best = per.groupby(level=[0, 1, 2]).min()

    def regret(rows):
        g = rows.groupby(["dataset", "budget_kib", "workload"]).fpr.mean()
        b = best.loc[g.index]
        rel = (g / b.where(b > 0)).fillna(1.0)
        ab = (g - b) * 1e6
        return rel, ab

    lines = ["# 实验 8：上限的模型推导与 N_eff 在线估计", "",
             f"模型参数：Zipf 指数范围 S = {list(S_RANGE)}，生命周期查询数 Q = {QUERIES:,}，N = 测试池大小；"
             "不拟合任何常数。代价相对“实验 7 与本实验所有候选比例里该负载最好的那个”。", "",
             "## 模型推出的比例 vs 实测", "",
             "| 数据集 | 预算 | 实验7最好的上限 | TOP-k 推出 | Che-LRU 推出 | 已知N规则(上限=Che) | "
             "各 s 下 Che 的最优比例 |", "|---|---:|---:|---:|---:|---:|---|"]
    e7sum = pd.DataFrame(json.loads((C.RESULTS / "exp7_cache_size_rule" / "summary.json").read_text()))
    for (ds, kib), g in picks.groupby(["dataset", "budget_kib"], sort=False):
        caps = e7sum[(e7sum.dataset == ds) & (e7sum.budget_kib == kib) & e7sum.pick.str.startswith("规则(上限")
                     & ~e7sum.pick.str.contains("N×")]
        best_cap = caps.loc[caps.worst_rel.idxmin()]
        tk = g[g.model == "TOP-k"].iloc[0]
        ch = g[g.model == "Che-LRU"].iloc[0]
        known = e8[(e8.dataset == ds) & (e8.budget_kib == kib) & (e8.pick == "规则(已知N,上限=Che)")].frac.iloc[0]
        per_s = ", ".join(f"{s}:{ch[f'best_s{s}']:.1%}" for s in S_RANGE)
        lines.append(f"| {ds} | {kib}KiB | {best_cap.pick[5:-1]}（{best_cap.worst_rel:.2f}×） | {tk.frac:.1%} | "
                     f"{ch.frac:.1%} | {known:.2%} | {per_s} |")

    lines += ["", "## 实测代价", "",
              "| 数据集 | 预算 | 选法 | 比例（中位数） | 最坏相对 | 相对中位数 | 最坏绝对（/百万） | 绝对中位数 |",
              "|---|---:|---|---:|---:|---:|---:|---:|"]
    summary = []
    for (ds, kib), g in e8.groupby(["dataset", "budget_kib"], sort=False):
        sets = {p: g[g.pick == p] for p in g.pick.unique()}
        e7g = e7[(e7.dataset == ds) & (e7.budget_kib == kib)]
        for _, r in e7r[(e7r.dataset == ds) & (e7r.budget_kib == kib) & (e7r.rule == "规则(上限40%)")].iterrows():
            sets["实验7规则(上限40%)"] = e7g[np.isclose(e7g.frac, round(r.frac, 6))]
        for name, rows in sets.items():
            rel, ab = regret(rows)
            row = {"dataset": ds, "budget_kib": kib, "pick": name, "frac_median": rows.frac.median(),
                   "worst_rel": rel.max(), "median_rel": rel.median(), "worst_rel_wl": rel.idxmax()[2],
                   "worst_abs": ab.max(), "median_abs": ab.median()}
            summary.append(row)
            lines.append(f"| {ds} | {kib}KiB | {name} | {row['frac_median']:.2%} | {row['worst_rel']:.2f}×"
                         f"（{row['worst_rel_wl']}） | {row['median_rel']:.2f}× | {row['worst_abs']:,.0f} | "
                         f"{row['median_abs']:,.1f} |")
    n = ev[ev.kind == "n_eff"]
    n = n.assign(err=n.n_eff / n.n_true_window - 1)
    lines += ["", f"HLL（{HLL_BYTES} 字节）对窗口内不同负 key 数的估计误差：中位数 {n.err.abs().median():.1%}，"
                  f"最大 {n.err.abs().max():.1%}。"]
    pd.DataFrame(summary).to_json(out / "summary.json", orient="records", force_ascii=False, indent=1)
    (out / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
