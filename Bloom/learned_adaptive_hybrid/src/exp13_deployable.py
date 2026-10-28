"""实验 13：可部署版本——只用学习期测量；以及控制器的阻尼 / 阈值修正。

Gama＋缓存（学习期校准）：误报流的三个量只在前 25% 查询上测，Q_F 按查询量线性外推到整个生命周期
（假设负载平稳）；据此联合选树数和缓存比例，在后 75% 上评估。观测误报少于 100 次时同实验 12 用先验。
控制器：树数取上面学习期校准选出的值（可部署），变体：阻尼（每次只走一半）、阈值（预测误报至少降 5%）、两者都开。
评估口径同实验 10。

用法：python src/exp13_deployable.py --dataset caida [--seeds 5] [--budgets ...]
      python src/exp13_deployable.py --report
"""

import argparse
import time

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp7_cache_size_rule import val_entry_bits
from exp8_cap_and_neff import FastEst
from exp9_fp_stream_controller import SKETCH_BYTES, BinMemo, run_controller
from exp11_original_baselines import GAMA_TREES, gama_scores, gama_setup
from exp12_gama_cache import HIGH, MIN_OBSERVED, FastEstT, joint_pick, measure
from exp9_fp_stream_controller import SETTINGS


OUT = C.RESULTS / "exp13_deployable"
VARIANTS = {"控制器(阻尼)": dict(damp=True), "控制器(阈值5%)": dict(thresh=0.05),
            "控制器(阻尼+阈值)": dict(damp=True, thresh=0.05)}


def run(ds, seeds, budgets):
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

    if ds.endswith("_flow"):
        wls, seeds = [("真实轨迹", None)], 1
    else:
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        wls = [(w[0], w[3]) for w in workloads(pools) if w[1] != "probe-replay"]
    rows = []
    dummy = np.zeros(1, np.int64)
    for name, spec in wls:
        for seed in range(seeds):
            stream = (C.load_flow_trace(setup) if spec is None
                      else make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order))
            q = stream.size
            tail = q // 4
            for kib in budgets:
                reserve = round(SKETCH_BYTES / (kib * 1024), 6)
                base = structure(48, kib, reserve)
                n_eff, QF, D_F, W, s_F = measure(setup, base, stream[:tail])      # 只看学习期
                p0 = est48(kib, reserve)
                QF_life = QF * q / tail if QF >= MIN_OBSERVED else 0.0
                n_u = max(n_eff, W / max(p0, 1e-12))
                t, f, _ = joint_pick(ests, kib, bbar, W, QF_life, s_F, n_u, q, p0, bins)
                s = structure(t, kib, f)
                full = int(simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                           np.zeros(1, np.bool_))[0])
                pre = int(simulate_policy(stream[:tail], s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                          np.zeros(1, np.bool_))[0])
                rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                             "method": "Gama＋缓存(学习期校准)", "trees": t, "frac": f, "fpr": (full - pre) / (q - tail)})
                b = structure(t, kib, reserve)
                for vname, kw in VARIANTS.items():
                    fpr_c, f_c, _ = run_controller(setup, ests[t], kib, stream, bbar, bins, b, tail_from=tail, **kw)
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                 "method": vname, "trees": t, "frac": f_c, "fpr": fpr_c})
        print(f"{ds} {name} done at {time.time() - t0:.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(OUT / f"rows_{ds}.json", orient="records", force_ascii=False, indent=1)


ORDER = ["Gama＋缓存", "Gama＋缓存(学习期校准)", "Gama模型＋在线控制器", "控制器(阻尼)", "控制器(阈值5%)",
         "控制器(阻尼+阈值)", "Gama-PLBF", "learned stacked(事后最优)", "Stacked(原版)"]


def report():
    parts = [pd.read_json(p) for d in ("exp10_baselines", "exp11_original_baselines", "exp12_gama_cache",
                                        "exp13_deployable") for p in sorted((C.RESULTS / d).glob("rows_*.json"))]
    df = pd.concat([p[["dataset", "budget_kib", "workload", "seed", "method", "fpr"]] for p in parts])
    a = df.groupby(["dataset", "budget_kib", "workload", "method"]).fpr.mean().reset_index()
    best = a.groupby(["dataset", "budget_kib", "workload"]).fpr.transform("min")
    eps = a.workload.map(lambda w: 1 / (0.75 * (5_775_801 if w == "真实轨迹" else 10_000_000)))
    a["rel"] = (a.fpr + eps) / (best + eps)
    a["abs_per_m"] = (a.fpr - best) * 1e6
    a.to_json(OUT / "summary.json", orient="records", force_ascii=False, indent=1)
    hi = {(d, b) for d, bs in HIGH.items() for b in bs}
    lines = ["# 实验 13：可部署版本（只用学习期测量）与控制器修正", "",
             "口径同实验 10–12。每格：所有负载上的最坏相对代价 / 中位数；★ 为高预算（看绝对值见实验 12）。"
             "“Gama＋缓存”= 实验 12 的全程测量版（带后见之明），“(学习期校准)”= 只用前 25% 测量，可部署。", "",
             "| 数据集 | 预算 | " + " | ".join(ORDER) + " |", "|---|---:|" + "---|" * len(ORDER)]
    for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=True):
        cells = [("—" if g[g.method == m].empty else
                  f"{g[g.method == m].rel.max():.2f}× / {g[g.method == m].rel.median():.2f}×") for m in ORDER]
        lines.append(f"| {ds} | {kib}KiB{' ★' if (ds, kib) in hi else ''} | " + " | ".join(cells) + " |")
    lo = a[~a.apply(lambda r: (r.dataset, r.budget_kib) in hi, axis=1)]
    lines += ["", "## 低预算设置汇总：各方法在所有设置上的最坏相对代价", "", "| 方法 | 最坏 | 最坏出现在 | 各设置最坏的中位数 |",
              "|---|---:|---|---:|"]
    for m in ORDER:
        h = lo[lo.method == m]
        if h.empty:
            continue
        per = h.groupby(["dataset", "budget_kib"]).rel.max()
        w = h.loc[h.rel.idxmax()]
        lines.append(f"| {m} | {h.rel.max():.2f}× | {w.dataset} {w.budget_kib}KiB {w.workload} | {per.median():.2f}× |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--budgets")
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        run(args.dataset, args.seeds,
            [int(b) for b in args.budgets.split(",")] if args.budgets else list(SETTINGS[args.dataset]) + list(HIGH[args.dataset]))
