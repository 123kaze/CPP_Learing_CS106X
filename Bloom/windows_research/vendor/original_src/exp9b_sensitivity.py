"""实验 9b：实验 8b 模型（N_eff 代入）对声明参数的敏感性。

变体：默认（S = {0,0.5,0.8,1.1,1.5}，Q = 1000 万）、S 只给 {0,0.5,0.8}、Q 偏小 4 倍、Q 偏大 4 倍。
N_eff 与 8b 相同（整条轨迹的 HLL，向上取整到档位）。比例网格在 0–2% 之间加密。
代价相对“实验 7、8、8b 与本实验所有候选里该负载最好的那个”（种子 0、1）。

用法：python src/exp9b_sensitivity.py
"""

import json
import time

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import QUERIES, make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp7_cache_size_rule import SETTINGS, val_entry_bits
from exp8_cap_and_neff import HLL_BYTES, FastEst, hll_estimate, model_fp, zipf_bins
from exp8b_model_neff import level


F_GRID = np.round(np.concatenate([[0.0, 0.001, 0.002, 0.005, 0.01, 0.015], np.arange(0.02, 0.8001, 0.01)]), 4)
VARIANTS = {"默认": ((0.0, 0.5, 0.8, 1.1, 1.5), QUERIES), "S只给[0,0.8]": ((0.0, 0.5, 0.8), QUERIES),
            "Q偏小4倍": ((0.0, 0.5, 0.8, 1.1, 1.5), QUERIES // 4), "Q偏大4倍": ((0.0, 0.5, 0.8, 1.1, 1.5), QUERIES * 4)}
SEEDS = 2


def pick(est, kib, n_eff, bbar, S, Q, memo, bins_memo):
    key = (kib, n_eff, S, Q)
    if key in memo:
        return memo[key]
    n = int(round(n_eff))
    reserve = HLL_BYTES / (kib * 1024)
    rel = []
    for s in S:
        if (n, s) not in bins_memo:
            bins_memo[(n, s)] = zipf_bins(n, s)
        c = []
        for f in F_GRID:
            if f < reserve or kib * 1024 * (1 - f) <= C.N_TREES * C.TREE_BYTES:
                c.append(np.inf)
                continue
            c.append(model_fp(est(kib, f), (f - reserve) * kib * 1024 * 8 / bbar, *bins_memo[(n, s)], Q)[1])
        c = np.array(c)
        rel.append(c / max(c.min(), 1e-12))
    f = float(F_GRID[int(np.argmin(np.max(rel, axis=0)))])
    memo[key] = f
    return f


def main():
    out = C.RESULTS / "exp9b_sensitivity"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows = []
    dummy = np.zeros(1, np.int64)
    for ds, budgets in SETTINGS.items():
        setup = C.Setup(ds)
        est = FastEst(setup)
        bbar = val_entry_bits(setup)
        n_pool = setup.q_score.size
        order = np.argsort(setup.q_score, kind="stable")
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        memo, bins_memo, built = {}, {}, {}
        for name, family, pool, spec, _ in [w for w in workloads(pools) if w[1] != "probe-replay"]:
            for seed in range(SEEDS):
                stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order)
                n_eff = level(hll_estimate(setup.h1q[stream]))
                for kib in budgets:
                    for var, (S, Q) in VARIANTS.items():
                        f = pick(est, kib, n_eff, bbar, S, Q, memo, bins_memo)
                        if (kib, f) not in built:
                            s = C.Structure(f"PLBF+缓存{f:.1%}", "bf", True, kib * 1024, setup, f)
                            s.fp_static = s.in_pass_q | s.bf_fp_q
                            built[(kib, f)] = s
                        s = built[(kib, f)]
                        r = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                            np.zeros(1, np.bool_))
                        rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                     "variant": var, "frac": f, "fpr": int(r[0]) / stream.size})
            print(f"{ds} {name} done at {time.time() - t0:.1f}s")
    df = pd.DataFrame(rows)
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))

    cols = ["dataset", "budget_kib", "workload", "seed", "frac", "fpr"]
    prev = [pd.DataFrame(json.loads((C.RESULTS / p).read_text())) for p in
            ("exp7_cache_size_rule/rows.json", "exp8_cap_and_neff/rows.json", "exp8_cap_and_neff/rows_b.json")]
    prev = [p[p.fpr.notna()][cols] for p in prev]
    allr = pd.concat(prev + [df[cols]])
    allr = allr[allr.seed < SEEDS]
    best = allr.groupby(["dataset", "budget_kib", "workload", "frac"]).fpr.mean().groupby(level=[0, 1, 2]).min()
    lines = ["# 实验 9b：模型对声明参数的敏感性", "",
             "代价相对“实验 7、8、8b 与本实验所有候选里该负载最好的那个”（种子 0、1）。", "",
             "| 数据集 | 预算 | 变体 | 比例范围 | 最坏相对（负载） | 相对中位数 |", "|---|---:|---|---|---|---:|"]
    for (ds, kib, var), g in df.groupby(["dataset", "budget_kib", "variant"], sort=False):
        m = g.groupby("workload").fpr.mean()
        b = best.loc[(ds, kib)].loc[m.index]
        rel = (m / b.where(b > 0)).fillna(1.0)
        lines.append(f"| {ds} | {kib}KiB | {var} | {g.frac.min():.1%}–{g.frac.max():.1%} | "
                     f"{rel.max():.2f}×（{rel.idxmax()}） | {rel.median():.2f}× |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"total {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
