"""实验 8b：把 HLL 估出的 N_eff 直接代入模型（不再用按全集 N 推出的上限）。

实验 8 发现：按全集 N 推上限时，模型以为查询分散在整个负例全集上，因而在“只查一小撮 key”的负载上
（例如 10 万 key 池的均匀负载）推出的比例过小。这里对每条轨迹：
  N_eff = HLL（2KB，从缓存预算里扣）统计整个生命周期内的不同负 key 数，向上取整到 2^(k/4) 的档位（宁可高估）
  比例  = Che-LRU 模型在 Zipf 指数范围 S 上最坏情况最好的比例，其中全集大小取 N_eff
比例网格 0–80%、步长 1%。模型仍不拟合任何常数。

用法：python src/exp8b_model_neff.py [--seeds 3]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import QUERIES, make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp7_cache_size_rule import SETTINGS, val_entry_bits
from exp8_cap_and_neff import HLL_BYTES, S_RANGE, FastEst, hll_estimate, model_fp, zipf_bins


F_GRID = np.round(np.arange(0.0, 0.8001, 0.01), 4)


def level(n):
    return 2.0 ** (np.ceil(4 * np.log2(max(n, 2))) / 4)


def model_pick(est, kib, n_eff, bbar, memo):
    key = (kib, n_eff)
    if key in memo:
        return memo[key]
    n = int(round(n_eff))
    bins = {s: zipf_bins(n, s) for s in S_RANGE}
    reserve = HLL_BYTES / (kib * 1024)
    curves = {s: [] for s in S_RANGE}
    for f in F_GRID:
        ok = f >= reserve and kib * 1024 * (1 - f) > C.N_TREES * C.TREE_BYTES
        p = est(kib, f) if ok else None
        for s in S_RANGE:
            if not ok:
                curves[s].append(np.inf)
                continue
            k = (f - reserve) * kib * 1024 * 8 / bbar
            curves[s].append(model_fp(p, k, *bins[s], QUERIES)[1])
    rel = np.array([np.array(c) / max(min(c), 1e-12) for c in curves.values()])
    f = float(F_GRID[int(np.argmin(rel.max(axis=0)))])
    memo[key] = f
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    out = C.RESULTS / "exp8_cap_and_neff"
    t0 = time.time()
    rows = []
    for ds, budgets in SETTINGS.items():
        setup = C.Setup(ds)
        est = FastEst(setup)
        bbar = val_entry_bits(setup)
        n_pool = setup.q_score.size
        order = np.argsort(setup.q_score, kind="stable")
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        memo, built = {}, {}
        dummy = np.zeros(1, np.int64)
        for name, family, pool, spec, _ in [w for w in workloads(pools) if w[1] != "probe-replay"]:
            for seed in range(args.seeds):
                stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order)
                n_eff = level(hll_estimate(setup.h1q[stream]))
                for kib in budgets:
                    f = model_pick(est, kib, n_eff, bbar, memo)
                    if (kib, f) not in built:
                        s = C.Structure(f"PLBF+缓存{f:.0%}", "bf", True, kib * 1024, setup, f)
                        s.fp_static = s.in_pass_q | s.bf_fp_q
                        built[(kib, f)] = s
                    s = built[(kib, f)]
                    res = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                          np.zeros(1, np.bool_))
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed, "kind": "eval",
                                 "pick": "模型(N_eff=HLL全程)", "frac": f, "n_eff": n_eff,
                                 "fpr": int(res[0]) / stream.size})
            print(f"{ds} {name} done at {time.time() - t0:.1f}s ({len(memo)} model evals)")
    df = pd.DataFrame(rows)
    (out / "rows_b.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))

    # 与实验 7、实验 8 的候选合并后统一算代价
    e7 = pd.DataFrame(json.loads((C.RESULTS / "exp7_cache_size_rule" / "rows.json").read_text()))
    e8 = pd.DataFrame(json.loads((out / "rows.json").read_text()))
    e8 = e8[e8.kind == "eval"]
    cols = ["dataset", "budget_kib", "workload", "seed", "frac", "fpr"]
    allr = pd.concat([e7[cols], e8[cols], df[cols]])
    per = allr.groupby(["dataset", "budget_kib", "workload", "frac"]).fpr.mean()
    best = per.groupby(level=[0, 1, 2]).min()
    lines = ["# 实验 8b：N_eff 直接代入模型", "",
             "代价相对“实验 7、8、8b 所有候选比例里该负载最好的那个”。“实验7规则(上限40%)”是事后挑上限的参照。", "",
             "| 数据集 | 预算 | 选法 | 比例范围 | 最坏相对 | 相对中位数 | 最坏绝对（/百万） | 绝对中位数 |",
             "|---|---:|---|---|---:|---:|---:|---:|"]
    e7r = pd.DataFrame(json.loads((C.RESULTS / "exp7_cache_size_rule" / "rules.json").read_text()))
    summary = []
    for ds, budgets in SETTINGS.items():
        for kib in budgets:
            sets = {"模型(N_eff=HLL全程)": df[(df.dataset == ds) & (df.budget_kib == kib)],
                    "规则+HLL(全程,上限=全集模型)": e8[(e8.dataset == ds) & (e8.budget_kib == kib)
                                                  & (e8.pick == "规则+HLL(前100%)")],
                    "模型(全集N)": e8[(e8.dataset == ds) & (e8.budget_kib == kib) & (e8.pick == "模型-Che-LRU")]}
            f40 = e7r[(e7r.dataset == ds) & (e7r.budget_kib == kib) & (e7r.rule == "规则(上限40%)")].frac.iloc[0]
            g7 = e7[(e7.dataset == ds) & (e7.budget_kib == kib)]
            sets["实验7规则(上限40%)"] = g7[np.isclose(g7.frac, round(f40, 6))]
            for name, r in sets.items():
                g = r.groupby("workload").fpr.mean()
                b = best.loc[(ds, kib)].loc[g.index]
                rel = (g / b.where(b > 0)).fillna(1.0)
                ab = (g - b) * 1e6
                summary.append({"dataset": ds, "budget_kib": kib, "pick": name, "worst_rel": rel.max(),
                                "median_rel": rel.median(), "worst_abs": ab.max(), "median_abs": ab.median(),
                                "worst_wl": rel.idxmax(), "frac_min": r.frac.min(), "frac_max": r.frac.max()})
                lines.append(f"| {ds} | {kib}KiB | {name} | {r.frac.min():.1%}–{r.frac.max():.1%} | "
                             f"{rel.max():.2f}×（{rel.idxmax()}） | {rel.median():.2f}× | {ab.max():,.0f} | {ab.median():,.1f} |")
    pd.DataFrame(summary).to_json(out / "summary_b.json", orient="records", force_ascii=False, indent=1)
    (out / "report_b.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
