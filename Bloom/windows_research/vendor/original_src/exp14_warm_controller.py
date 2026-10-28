"""实验 14：离线校准＋在线补充——控制器从学习期校准的结果出发，之后只增不减。

三者放在同一张表（同一批轨迹、同样的学习期选择）：
  学习期校准       只用前 25% 测误报流，联合选树数 t 与缓存比例 f（同实验 13），之后不动
  控制器(从0)      树数取 t，缓存从 0 开始只增不减（无阻尼、无阈值）
  控制器(从离线起) 树数取 t，按比例 f 分配好过滤器、缓存容量从 f 开始，之后只增不减
评估口径同实验 10：只比后 75%；报告相对代价和每百万次查询的绝对代价。

用法：python src/exp14_warm_controller.py --dataset caida [--seeds 5]
      python src/exp14_warm_controller.py --report
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
from exp9_fp_stream_controller import SETTINGS, SKETCH_BYTES, BinMemo, run_controller
from exp11_original_baselines import GAMA_TREES, gama_scores, gama_setup
from exp12_gama_cache import HIGH, MIN_OBSERVED, FastEstT, joint_pick, measure


OUT = C.RESULTS / "exp14_warm_controller"
METHODS = ("学习期校准", "控制器(从0)", "控制器(从离线起)")
DRIFTING = {"向难负例漂移"}                     # 负载在学习期之后才出现热点
STATIONARY_EXCLUDE = DRIFTING | {"全新对抗"}


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
                n_eff, QF, D_F, W, s_F = measure(setup, structure(48, kib, reserve), stream[:tail])
                p0 = est48(kib, reserve)
                QF_life = QF * q / tail if QF >= MIN_OBSERVED else 0.0
                t, f, _ = joint_pick(ests, kib, bbar, W, QF_life, s_F, max(n_eff, W / max(p0, 1e-12)), q, p0, bins)
                s = structure(t, kib, f)
                full = int(simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, 1, dummy, np.zeros(1, np.bool_))[0])
                pre = int(simulate_policy(stream[:tail], s.fp_static, s.cache_cost, s.cache_bits, 1, dummy,
                                          np.zeros(1, np.bool_))[0])
                res = {"学习期校准": ((full - pre) / (q - tail), f)}
                fpr0, f0, _ = run_controller(setup, ests[t], kib, stream, bbar, bins, structure(t, kib, reserve),
                                             tail_from=tail)
                res["控制器(从0)"] = (fpr0, f0)
                warm_cap = max(0, s.cache_bits - SKETCH_BYTES * 8)
                fprw, fw, _ = run_controller(setup, ests[t], kib, stream, bbar, bins, s, tail_from=tail, init_cap=warm_cap)
                res["控制器(从离线起)"] = (fprw, fw)
                for m, (fpr, frac) in res.items():
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed, "method": m,
                                 "trees": t, "frac_offline": f, "frac": frac, "fpr": fpr})
        print(f"{ds} {name} done at {time.time() - t0:.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(OUT / f"rows_{ds}.json", orient="records", force_ascii=False, indent=1)


def report():
    parts = [pd.read_json(p) for d in ("exp10_baselines", "exp11_original_baselines", "exp12_gama_cache",
                                        "exp13_deployable", "exp14_warm_controller")
             for p in sorted((C.RESULTS / d).glob("rows_*.json"))]
    df = pd.concat([p[["dataset", "budget_kib", "workload", "seed", "method", "fpr"]] for p in parts])
    a = df.groupby(["dataset", "budget_kib", "workload", "method"]).fpr.mean().reset_index()
    best = a.groupby(["dataset", "budget_kib", "workload"]).fpr.transform("min")
    eps = a.workload.map(lambda w: 1 / (0.75 * (5_775_801 if w == "真实轨迹" else 10_000_000)))
    a["rel"] = (a.fpr + eps) / (best + eps)
    a["abs_per_m"] = (a.fpr - best) * 1e6
    a = a[a.method.isin(METHODS)]
    a.to_json(OUT / "summary.json", orient="records", force_ascii=False, indent=1)
    hi = {(d, b) for d, bs in HIGH.items() for b in bs}
    lines = ["# 实验 14：离线校准＋在线补充（控制器从学习期校准的结果出发）", "",
             "口径同实验 10–13（只比后 75%；相对代价对“所有方法与网格里该负载最好的那个”，各加 1 次误报平滑）。"
             "三种方法用同一个学习期选择（树数 t、比例 f）。", ""]
    for title, sel in (("平稳负载（去掉难负例漂移和全新对抗）", lambda g: ~g.workload.isin(STATIONARY_EXCLUDE)),
                       ("难负例漂移", lambda g: g.workload.isin(DRIFTING)), ("全部负载", lambda g: g.workload == g.workload)):
        lines += [f"## {title}：最坏相对 / 中位数；最坏绝对（每百万次查询多出的误报）", "",
                  "| 数据集 | 预算 | " + " | ".join(METHODS) + " |", "|---|---:|" + "---|" * len(METHODS)]
        for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=True):
            g = g[sel(g)]
            if g.empty:
                continue
            cells = []
            for m in METHODS:
                h = g[g.method == m]
                cells.append(f"{h.rel.max():.2f}× / {h.rel.median():.2f}×；{h.abs_per_m.max():,.1f}")
            lines.append(f"| {ds} | {kib}KiB{' ★' if (ds, kib) in hi else ''} | " + " | ".join(cells) + " |")
        lines.append("")
    lo = a[[(d, b) not in hi for d, b in zip(a.dataset, a.budget_kib)]]
    lines += ["## 低预算汇总", "", "| 方法 | 平稳负载最坏相对 | 全部负载最坏相对 | 漂移负载最坏绝对（/百万） | 全部负载各设置最坏绝对的中位数 |",
              "|---|---:|---:|---:|---:|"]
    for m in METHODS:
        h = lo[lo.method == m]
        st = h[~h.workload.isin(STATIONARY_EXCLUDE)]
        dr = h[h.workload.isin(DRIFTING)]
        lines.append(f"| {m} | {st.rel.max():.2f}× | {h.rel.max():.2f}× | {dr.abs_per_m.max():,.0f} | "
                     f"{h.groupby(['dataset', 'budget_kib']).abs_per_m.max().median():,.0f} |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--report", action="store_true")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        run(args.dataset, args.seeds, list(SETTINGS[args.dataset]) + list(HIGH[args.dataset]))
