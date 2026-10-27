"""实验 1：朴素 learned+adaptive 混合后，剩下的误报有多少来自模型直接放行。

结构：BF / AQF / PLBF / PLBF+AQF，同一内存预算（模型内存计入）。
负载：uniform / zipf1.0 / zipf1.5 / 天区漂移 / 2% 与 10% 探测重放对抗。
只模拟非成员查询；成员不会被拒（构建时逐个核对）。

用法：python src/exp1_fp_source.py [--seeds 10]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

import common as C


BUDGETS_KIB = (256, 1024, 4096)
QUERIES = 10_000_000
DRIFT_WINDOW = 50_000
OUT = C.RESULTS / "exp1_fp_source"

# adv*：探测重放对抗（见 results/checks/checks.md 第 3 条），属于重复型负载
WORKLOADS = {"uniform": 0.0, "zipf1.0": 0.0, "zipf1.5": 0.0, "drift": 0.0,
             "adv2%": 0.02, "adv10%": 0.10}


def make_stream(workload, n_pool, rng, ra_order):
    if workload.startswith("zipf"):
        a = float(workload[4:])
        cdf = np.cumsum(np.arange(1, n_pool + 1, dtype=np.float64) ** -a)
        ranks = np.searchsorted(cdf / cdf[-1], rng.random(QUERIES))
        return rng.permutation(n_pool)[np.minimum(ranks, n_pool - 1)]
    if workload == "drift":
        start = np.arange(QUERIES, dtype=np.int64) * (n_pool - DRIFT_WINDOW) // QUERIES
        return ra_order[start + rng.integers(0, DRIFT_WINDOW, QUERIES)]
    return rng.integers(0, n_pool, QUERIES)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=10)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setup = C.Setup()
    ra_order = np.argsort(setup.q_ra, kind="stable")
    no_ref = np.zeros(setup.q_score.size, np.bool_)

    structures = []
    for kib in BUDGETS_KIB:
        for name, filt, use_model in (("BF", "bf", False), ("AQF", "aqf", False),
                                      ("PLBF", "bf", True), ("PLBF+AQF", "aqf", True)):
            s = C.Structure(name, filt, use_model, kib * 1024, setup)
            structures.append(s)
            info = s.summary()
            print(f"{kib:>5}KiB {name:<9} feasible={info['feasible']} "
                  f"filter={info['filter_bytes']}B est_val_fpr={info['est_val_fpr']:.4%} "
                  f"pass_regions={info['pass_regions']} in_filter={info['members_in_filter']}")

    rows = []
    for wl, adv_p in WORKLOADS.items():
        for seed in range(args.seeds):
            stream = make_stream(wl, setup.q_score.size, np.random.default_rng(1000 + seed), ra_order)
            for s in structures:
                if not s.feasible:
                    continue
                res, used_reserve = s.run(stream, adv_p, 7 + seed, no_ref)
                fp_pass, fp_filter = int(res[C.FP_PASS]), int(res[C.FP_FILTER])
                fp = fp_pass + fp_filter
                rows.append({
                    "budget_kib": s.budget_kib, "structure": s.name, "workload": wl, "seed": seed,
                    "fpr": fp / QUERIES,
                    "fpr_tail20": int(res[C.FP_TAIL]) / (QUERIES - int(QUERIES * 0.8)),
                    "fpr_filter_only": fp_filter / QUERIES,
                    "pass_share": fp_pass / fp if fp else 0.0,
                    "adaptations": int(res[C.ADAPTS]), "reserve_used": used_reserve,
                    "reserve_total": int(s.reserve0.sum()), "adv_queries": int(res[C.ADV_N]),
                    "fp_pass_count": fp_pass, "fp_filter_count": fp_filter,
                })
        print(f"workload {wl} done at {time.time() - t0:.1f}s")

    meta = {"structures": [s.summary() for s in structures],
            "queries": QUERIES, "seeds": args.seeds,
            "params": {"N_TREES": C.N_TREES, "TREE_BYTES": C.TREE_BYTES, "N_SEG": C.N_SEG,
                       "ALPHA": C.ALPHA, "META_BITS": C.META_BITS, "RESERVE": C.RESERVE,
                       "DRIFT_WINDOW": DRIFT_WINDOW, "ADV_REPLAY": C.ADV_REPLAY}}
    (OUT / "rows.json").write_text(json.dumps(rows, indent=1))
    (OUT / "meta.json").write_text(json.dumps(meta, indent=1))
    report(pd.DataFrame(rows), meta)
    print(f"total {time.time() - t0:.1f}s")


def report(df, meta):
    lines = ["# 实验 1：朴素混合误报来源", "",
             f"每次运行 {meta['queries']:,} 条非成员查询，{meta['seeds']} 个种子；"
             "表中为均值，括号内为种子间最小–最大。adv* 为探测重放对抗（重复型）。", ""]
    lines += ["## 结构配置", "", "| 预算 | 结构 | 可行 | 模型B | 过滤器B | 验证集估计FPR | 直接放行段数 | 过滤器内成员 |",
              "|---:|---|---|---:|---:|---:|---:|---:|"]
    for s in meta["structures"]:
        lines.append(f"| {s['budget_kib']}KiB | {s['name']} | {'是' if s['feasible'] else '否'} | "
                     f"{s['model_bytes']} | {s['filter_bytes']} | {s['est_val_fpr']:.4%} | "
                     f"{s['pass_regions']} | {s['members_in_filter']:,} |")

    def cell(g, col, pct=True):
        f = (lambda v: f"{v:.3%}") if pct else (lambda v: f"{v:.1%}")
        return f"{f(g[col].mean())} ({f(g[col].min())}–{f(g[col].max())})"

    wls = list(WORKLOADS)
    for col, title in (("fpr", "整体 FPR"), ("fpr_tail20", "最后 20% 查询的 FPR")):
        lines += ["", f"## {title}", ""]
        lines += ["| 预算 | 结构 | " + " | ".join(wls) + " |", "|---:|---|" + "---:|" * len(wls)]
        for (kib, name), g in df.groupby(["budget_kib", "structure"], sort=False):
            cells = [cell(g[g.workload == w], col) for w in wls]
            lines.append(f"| {kib}KiB | {name} | " + " | ".join(cells) + " |")

    lines += ["", "## 原始误报次数（10 个种子合计；直接放行 / 过滤器）", ""]
    lines += ["| 预算 | 结构 | " + " | ".join(wls) + " |", "|---:|---|" + "---:|" * len(wls)]
    for (kib, name), g in df.groupby(["budget_kib", "structure"], sort=False):
        cells = [f"{g[g.workload == w].fp_pass_count.sum():,} / {g[g.workload == w].fp_filter_count.sum():,}"
                 for w in wls]
        lines.append(f"| {kib}KiB | {name} | " + " | ".join(cells) + " |")

    lines += ["", "## 关键指标：PLBF+AQF 剩余误报中来自模型直接放行的比例", "",
              "| 预算 | 负载 | 直接放行占比 | 整体 FPR | 若直接放行误报全部消除 | 扩展次数 | 预留槽用量 |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    hyb = df[df.structure == "PLBF+AQF"]
    for (kib, wl), g in hyb.groupby(["budget_kib", "workload"], sort=False):
        lines.append(f"| {kib}KiB | {wl} | {cell(g, 'pass_share', pct=False)} | "
                     f"{g.fpr.mean():.3%} | {g.fpr_filter_only.mean():.4%} | "
                     f"{g.adaptations.mean():.0f} | {g.reserve_used.mean():.0f}/{g.reserve_total.iloc[0]} |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
