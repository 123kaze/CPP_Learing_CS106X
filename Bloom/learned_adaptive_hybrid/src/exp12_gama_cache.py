"""实验 12：在 Gama 的分配里加一维缓存——Gama 是缓存比例 r = 0 的特例。

离线（Gama＋缓存）：对 Gama 的每个候选树数 t（200 轮模型的前缀），用误报流模型选缓存比例，取 (t, r) 联合最优。
  误报流的测量只在 48 树基础结构上做一次（整条轨迹，带后见之明，同实验 9/10 的静态版）：(Q_F, D_F, 头部占比) → (W, s_F)。
  换模型：s_F 沿用；W、Q_F 按估计 FPR 等比例换算到候选模型的“无缓存”状态：W_t = W·p_t/p_48；
  同一模型内部随缓存比例变化仍按加性计入（实验 9 的做法）。
  验证换算：对 3 个候选树数（最小可行、48、Gama 选的）直接在该模型上测 (W, s_F, Q_F)，与换算值对比。
在线（Gama模型＋控制器）：树数固定为离线选出的 t，控制器只调缓存（不换模型，保持“每一步都不重建”）。
评估口径同实验 10：前 25% 学习期，只比后 75%。

用法：python src/exp12_gama_cache.py --dataset caida [--seeds 5] [--budgets 128,256,1024] [--suffix ""]
      python src/exp12_gama_cache.py --report
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp7_cache_size_rule import val_entry_bits
from exp8_cap_and_neff import FastEst
from exp9_fp_stream_controller import (F_MODEL, HLL_P, SETTINGS, SKETCH_BYTES, SS_K, BinMemo, fit_stream,
                                       fp_stream_misses, hll_count, hll_fill, run_controller, space_saving_top_mass)
from exp11_original_baselines import GAMA_TREES, gama_scores, gama_setup


OUT = C.RESULTS / "exp12_gama_cache"
HIGH = {"cod": (4096,), "caida": (2048,), "shalla": (4096,), "caida_flow": (256,), "mawi2020_flow": (128,),
        "mawi2021_flow": (128,)}
MIN_OBSERVED = 100          # 基础结构上观测到的误报少于这个数时，换模型改用先验


class FastEstT(FastEst):
    """FastEst 的任意树数版本：模型占 t × 700 字节。"""

    def __init__(self, setup, t):
        super().__init__(setup)
        self.t = t

    def __call__(self, kib, f):
        key = (kib, round(f, 6))
        if key not in self.memo:
            budget = (kib * 1024 - self.t * C.TREE_BYTES) * 8 - int(kib * 1024 * f) * 8
            self.memo[key] = C.allocate(self.n, self.h, budget, "bf")[3] if budget > 0 else 1.0
        return self.memo[key]


def measure(setup, base, stream):
    fs = stream[base.fp_static[stream]]
    nr = np.zeros(1 << HLL_P, np.int64)
    fr = np.zeros(1 << HLL_P, np.int64)
    hll_fill(nr, setup.h1q[stream])
    hll_fill(fr, setup.h1q[fs])
    n_eff, D_F, QF = hll_count(nr), hll_count(fr), fs.size
    W, s_F = fit_stream(QF, D_F, space_saving_top_mass(fs, SS_K)) if QF else (1.0, 0.0)
    return n_eff, QF, D_F, W, s_F


def joint_pick(ests, kib, bbar, W0, QF0, s_F, n_u, Q, p0, bins):
    """返回 (t, f, 预测误报)。ests: {t: FastEstT}；W0、QF0 是 48 树基础结构（草图预留比例）上测的。"""
    reserve = SKETCH_BYTES / (kib * 1024)
    best = (None, None, np.inf, np.inf)
    for t, est in ests.items():
        if t * C.TREE_BYTES >= kib * 1024 * (1 - reserve):
            continue
        pt0 = est(kib, reserve)
        if QF0 >= MIN_OBSERVED:
            Wt, QFt = W0 * pt0 / p0, QF0 * pt0 / p0             # 换模型：按估计 FPR 等比例换算
        else:                                                   # 观测到的误报太少：用验证集估计 FPR 作先验
            Wt, QFt = n_u * pt0, Q * pt0
        for f in F_MODEL:
            f = max(float(f), reserve)
            if kib * 1024 * (1 - f) <= t * C.TREE_BYTES:
                continue
            dp = est(kib, f) - pt0                               # 同一模型内：加性
            m = fp_stream_misses(Wt + n_u * dp, s_F, QFt + Q * dp, (f - reserve) * kib * 1024 * 8 / bbar, bins)
            pf = pt0 + dp
            if m < best[2] - 1e-9 or (abs(m - best[2]) <= 1e-9 and pf < best[3]):   # 打平时按 Gama 的准则
                best = (t, round(f, 4), m, pf)
    return best[:3]


def run(ds, seeds, budgets, suffix):
    t0 = time.time()
    setup = C.Setup(ds)
    n_pool = setup.q_score.size
    order = np.argsort(setup.q_score, kind="stable")
    bbar = val_entry_bits(setup)
    bins = BinMemo()
    scores = gama_scores(setup, ds)
    gsetups = {t: gama_setup(setup, scores[t]) for t in GAMA_TREES}
    ests = {t: FastEstT(gsetups[t], t) for t in GAMA_TREES}
    est48 = FastEst(setup)
    built = {}

    def structure(t, kib, f):
        key = (t, kib, round(f, 6))
        if key not in built:
            s = C.Structure(f"t{t}-{f:.3f}", "bf", True, kib * 1024, gsetups[t] if t != 48 else setup, f, n_trees=t)
            s.fp_static = s.in_pass_q | s.bf_fp_q
            built[key] = s
        return built[key]

    # Gama 自己（r = 0）选的树数，用来挑验证换算的候选
    gama_t = {}
    for kib in budgets:
        cands = [(ests[t](kib, 0.0), t) for t in GAMA_TREES if t * C.TREE_BYTES < kib * 1024]
        gama_t[kib] = min(cands)[1]
    if ds.endswith("_flow"):
        wls, seeds = [("真实轨迹", None)], 1
    else:
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        wls = [(w[0], w[3]) for w in workloads(pools) if w[1] != "probe-replay"]
    rows, checks = [], []
    dummy = np.zeros(1, np.int64)
    for name, spec in wls:
        for seed in range(seeds):
            stream = (C.load_flow_trace(setup) if spec is None
                      else make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order))
            q = stream.size
            tail = q // 4

            def tail_rate(fn):
                return (fn(stream) - fn(stream[:tail])) / (q - tail)

            for kib in budgets:
                reserve = round(SKETCH_BYTES / (kib * 1024), 6)
                base = structure(48, kib, reserve)
                n_eff, QF, D_F, W, s_F = measure(setup, base, stream)
                p0 = est48(kib, reserve)
                n_u = max(n_eff, W / max(p0, 1e-12))
                t, f, _ = joint_pick(ests, kib, bbar, W, QF, s_F, n_u, q, p0, bins)
                s = structure(t, kib, f)
                fpr = tail_rate(lambda st: int(simulate_policy(st, s.fp_static, s.cache_cost, s.cache_bits, 1,
                                                               dummy, np.zeros(1, np.bool_))[0]))
                rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                             "method": "Gama＋缓存", "frac": f, "trees": t, "fpr": fpr})
                b = structure(t, kib, reserve)
                fpr_c, f_c, _ = run_controller(setup, ests[t], kib, stream, bbar, bins, b, tail_from=tail)
                rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                             "method": "Gama模型＋在线控制器", "frac": f_c, "trees": t, "fpr": fpr_c})
                # 验证换模型时的换算：只在种子 0 上做
                if seed == 0:
                    feasible = [x for x in GAMA_TREES if x * C.TREE_BYTES < kib * 1024 * (1 - reserve)]
                    for tc in sorted({feasible[0], 48, gama_t[kib]}):
                        if tc not in feasible:
                            continue
                        bt = structure(tc, kib, reserve)
                        _, QFt, D_Ft, Wt, s_t = measure(setup, bt, stream)
                        r = ests[tc](kib, reserve) / p0
                        checks.append({"dataset": ds, "budget_kib": kib, "workload": name, "trees": tc,
                                       "W_measured": Wt, "W_scaled": W * r, "QF_measured": QFt, "QF_scaled": QF * r,
                                       "s_measured": s_t, "s_carried": s_F})
        print(f"{ds} {name} done at {time.time() - t0:.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(OUT / f"rows_{ds}{suffix}.json", orient="records", force_ascii=False, indent=1)
    pd.DataFrame(checks).to_json(OUT / f"checks_{ds}{suffix}.json", orient="records", force_ascii=False, indent=1)


ORDER = ["Gama-PLBF", "Gama＋缓存", "Gama模型＋在线控制器", "误报流模型", "在线控制器", "Stacked(原版)",
         "learned stacked(事后最优)", "SkiQF式二次准入", "TODS-CAF(PLBF)", "纯AQF", "PLBF(0%缓存)"]


def report():
    parts = [pd.read_json(p) for d in ("exp10_baselines", "exp11_original_baselines", "exp12_gama_cache")
             for p in sorted((C.RESULTS / d).glob("rows_*.json"))]
    df = pd.concat([p[["dataset", "budget_kib", "workload", "seed", "method", "fpr"]] for p in parts])
    a = df.groupby(["dataset", "budget_kib", "workload", "method"]).fpr.mean().reset_index()
    best = a.groupby(["dataset", "budget_kib", "workload"]).fpr.transform("min")
    eps = a.workload.map(lambda w: 1 / (0.75 * (5_775_801 if w == "真实轨迹" else 10_000_000)))
    a["rel"] = (a.fpr + eps) / (best + eps)
    a["abs_per_m"] = (a.fpr - best) * 1e6
    a.to_json(OUT / "summary.json", orient="records", force_ascii=False, indent=1)
    hi = {(d, b) for d, bs in HIGH.items() for b in bs}
    lines = ["# 实验 12：Gama＋缓存（Gama 是 r = 0 的特例）与高预算对比", "",
             "口径同实验 10：前 25% 学习期，只比后 75%；相对“网格比例与所有方法里该负载最好的那个”，各加 1 次误报平滑。"
             "每格：所有负载上的最坏相对代价 / 中位数。标 ★ 的是每成员 ≥8 bit 的高预算设置。", "",
             "| 数据集 | 预算 | " + " | ".join(ORDER) + " |", "|---|---:|" + "---|" * len(ORDER)]
    for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=True):
        cells = []
        for m in ORDER:
            h = g[g.method == m]
            cells.append("—" if h.empty else f"{h.rel.max():.2f}× / {h.rel.median():.2f}×")
        star = " ★" if (ds, kib) in hi else ""
        lines.append(f"| {ds} | {kib}KiB{star} | " + " | ".join(cells) + " |")
    # 高预算：相对代价被 ~0 的 FPR 放大，改看绝对值
    lines += ["", "## 高预算设置（★）的绝对代价：所有负载上最坏 / 中位数，每百万次查询多出的误报", "",
              "| 数据集 | 预算 | " + " | ".join(ORDER) + " |", "|---|---:|" + "---|" * len(ORDER)]
    for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=True):
        if (ds, kib) not in hi:
            continue
        cells = []
        for m in ORDER:
            h = g[g.method == m]
            cells.append("—" if h.empty else f"{h.abs_per_m.max():,.1f} / {h.abs_per_m.median():,.1f}")
        lines.append(f"| {ds} | {kib}KiB | " + " | ".join(cells) + " |")
    # 无重复负载：Gama＋缓存 能否追平 Gama
    nr = a[a.workload.isin(["每key一次", "全新对抗"]) & a.method.isin(["Gama-PLBF", "Gama＋缓存"])]
    piv = nr.pivot_table(index=["dataset", "budget_kib", "workload"], columns="method", values="fpr")
    if not piv.empty:
        e = 1 / 7.5e6
        ratio = ((piv["Gama＋缓存"] + e) / (piv["Gama-PLBF"] + e)).describe()
        lines += ["", f"无重复负载上 (Gama＋缓存 + ε) ÷ (Gama-PLBF + ε)：中位数 {ratio['50%']:.3f}，最大 {ratio['max']:.3f}"
                      "（差距来自草图占用的那部分预算）。"]
    ch = pd.concat([pd.read_json(p) for p in sorted(OUT.glob("checks_*.json"))])
    ch = ch[ch.W_measured > 0]
    w = (ch.W_scaled / ch.W_measured)
    qf = (ch.QF_scaled / ch.QF_measured.clip(lower=1))
    lines += ["", "## 换模型时的换算验证（种子 0，所有负载）", "",
              f"W 换算 ÷ 实测：中位数 {w.median():.2f}，10–90 分位 {w.quantile(0.1):.2f}–{w.quantile(0.9):.2f}；"
              f"Q_F 换算 ÷ 实测：中位数 {qf.median():.2f}，10–90 分位 {qf.quantile(0.1):.2f}–{qf.quantile(0.9):.2f}；"
              f"|s_F 沿用 − 实测| 中位数 {(ch.s_carried - ch.s_measured).abs().median():.2f}。", "",
              "| 数据集 | 预算 | 树数 | W 换算÷实测（中位数） | Q_F 换算÷实测（中位数） |", "|---|---:|---:|---:|---:|"]
    for (ds, kib, t), g in ch.groupby(["dataset", "budget_kib", "trees"]):
        lines.append(f"| {ds} | {kib}KiB | {t} | {(g.W_scaled / g.W_measured).median():.2f} | "
                     f"{(g.QF_scaled / g.QF_measured.clip(lower=1)).median():.2f} |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--budgets")
    ap.add_argument("--suffix", default="")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        run(args.dataset, args.seeds,
            [int(b) for b in args.budgets.split(",")] if args.budgets else list(SETTINGS[args.dataset]), args.suffix)
