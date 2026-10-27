"""实验 7：部署前可算的缓存大小规则，对比事后在网格上挑出的稳健比例。

规则：比例 f = min(W(f)·b̄ / 预算, 上限)，用不动点迭代求解。
  W(f)  = PLBF（预算扣掉缓存后）在验证集上的估计 FPR × 负例全集大小 N（假定部署前已知）
  b̄     = 验证集负例的平均缓存条目位数（与全部成员都不冲突的最短前缀 + 6 bit）
  上限  = 20% / 30% / 40%
敏感性：N 估成实际的 0.5 倍和 2 倍（上限 30%）。
对照：网格上按“最坏相对代价最小”和“最坏绝对代价最小”分别挑出的固定比例（事后挑，带后见之明）。
缓存一律 LRU；基础结构是静态 PLBF，用实验 4 的模拟器。

用法：python src/exp7_cache_size_rule.py [--seeds 3]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp4_cache_policy import simulate_policy


GRID = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.30, 0.40, 0.60)
CAPS = (0.20, 0.30, 0.40)
SETTINGS = {"cod": (256, 1024), "caida": (128, 256, 1024), "shalla": (256, 1024, 2048)}


def val_entry_bits(setup):
    h1v = C.splitmix64(setup.ids[setup.split["neg_val"]] ^ np.uint64(C.H1_SALT))
    out = np.zeros(h1v.size, np.int64)
    C.cache_entry_bits(np.sort(setup.h1m), h1v, np.ones(h1v.size, np.bool_), out)
    return float(out[out > 0].mean())


def rule_fraction(setup, kib, n_universe, bbar, cap):
    f = 0.0
    for _ in range(30):
        if kib * 1024 * (1 - f) <= C.N_TREES * C.TREE_BYTES:
            return cap
        est = C.Structure("tmp", "bf", True, kib * 1024, setup, f).est_fpr
        f_new = min(est * n_universe * bbar / (kib * 1024 * 8), cap)
        if abs(f_new - f) < 1e-4:
            return f_new
        f = 0.5 * f + 0.5 * f_new
    return f


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=3)
    args = ap.parse_args()
    out = C.RESULTS / "exp7_cache_size_rule"
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rows, rules = [], []
    for ds, budgets in SETTINGS.items():
        setup = C.Setup(ds)
        n_pool = setup.q_score.size
        order = np.argsort(setup.q_score, kind="stable")
        bbar = val_entry_bits(setup)
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        structs = []
        for kib in budgets:
            fracs = {f: f"网格{f:.0%}" for f in GRID if kib * 1024 * (1 - f) > C.N_TREES * C.TREE_BYTES}
            for cap in CAPS:
                f = rule_fraction(setup, kib, n_pool, bbar, cap)
                rules.append({"dataset": ds, "budget_kib": kib, "rule": f"规则(上限{cap:.0%})", "frac": f})
                fracs.setdefault(round(f, 6), None)
            for mult in (0.5, 2.0):
                f = rule_fraction(setup, kib, n_pool * mult, bbar, 0.30)
                rules.append({"dataset": ds, "budget_kib": kib, "rule": f"规则(上限30%,N×{mult:g})", "frac": f})
                fracs.setdefault(round(f, 6), None)
            for f in fracs:
                s = C.Structure(f"PLBF+缓存{f:.2%}", "bf", True, kib * 1024, setup, f)
                s.fp_static = s.in_pass_q | s.bf_fp_q
                structs.append(s)
        print(f"{ds}: b̄={bbar:.1f} bit, {len(structs)} structures at {time.time() - t0:.1f}s")
        dummy = np.zeros(1, np.int64)
        for name, family, pool, spec, _ in [w for w in workloads(pools) if w[1] != "probe-replay"]:
            for seed in range(args.seeds):
                stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order)
                for s in structs:
                    res = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                          np.zeros(1, np.bool_))
                    rows.append({"dataset": ds, "budget_kib": s.budget_kib, "frac": round(s.cache_frac, 6),
                                 "workload": name, "seed": seed, "fpr": int(res[0]) / stream.size})
        print(f"{ds} done at {time.time() - t0:.1f}s")
    df = pd.DataFrame(rows)
    rl = pd.DataFrame(rules)
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    (out / "rules.json").write_text(rl.to_json(orient="records", force_ascii=False, indent=1))
    report(df, rl, out)
    print(f"total {time.time() - t0:.1f}s")


def report(df, rl, out):
    a = df.groupby(["dataset", "budget_kib", "workload", "frac"]).fpr.mean()
    lines = ["# 实验 7：部署前可算的缓存大小规则", "",
             "代价都相对“该负载在所有候选比例（网格 + 各规则点）里最好的那个”：相对代价 = FPR ÷ 最好 FPR；"
             "绝对代价 = (FPR − 最好 FPR) × 10⁶，即每百万次查询多出的误报次数。"
             "“稳健-相对”“稳健-绝对”是事后在网格上挑出、使最坏相对 / 绝对代价最小的固定比例（带后见之明）。", "",
             "| 数据集 | 预算 | 选法 | 比例 | 最坏相对 | 相对中位数 | 最坏绝对（/百万） | 绝对中位数 |",
             "|---|---:|---|---:|---:|---:|---:|---:|"]
    summary = []
    for (ds, kib), g in a.groupby(level=["dataset", "budget_kib"]):
        piv = g.droplevel([0, 1]).unstack("frac")
        best = piv.min(axis=1)
        rel = piv.div(best.where(best > 0), axis=0).fillna(1.0)
        ab = piv.sub(best, axis=0) * 1e6
        grid = [f for f in piv.columns if any(abs(f - x) < 1e-9 for x in GRID)]
        picks = {"稳健-相对": rel[grid].max().idxmin(), "稳健-绝对": ab[grid].max().idxmin()}
        for _, r in rl[(rl.dataset == ds) & (rl.budget_kib == kib)].iterrows():
            picks[r.rule] = round(r.frac, 6)
        for name, f in picks.items():
            row = {"dataset": ds, "budget_kib": kib, "pick": name, "frac": f, "worst_rel": rel[f].max(),
                   "median_rel": rel[f].median(), "worst_abs": ab[f].max(), "median_abs": ab[f].median(),
                   "worst_rel_wl": rel[f].idxmax(), "worst_abs_wl": ab[f].idxmax()}
            summary.append(row)
            lines.append(f"| {ds} | {kib}KiB | {name} | {f:.2%} | {row['worst_rel']:.2f}× | {row['median_rel']:.2f}× | "
                         f"{row['worst_abs']:,.0f}（{row['worst_abs_wl']}） | {row['median_abs']:,.1f} |")
    pd.DataFrame(summary).to_json(out / "summary.json", orient="records", force_ascii=False, indent=1)
    (out / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
