"""实验 10：与更强的基线对比（同一预算、同一批负载，合成负载 5 个种子 + 真实轨迹）。

我们的方法：
  误报流模型      实验 9 的静态版（整条轨迹上测 Q_F、D_F、头部占比 → 比例；草图开销计入）
  在线控制器      实验 9 的只增不减版
基线：
  PLBF（0% 缓存）               原版 Gama/PLBF 的形态（模型固定 48 树，没有复现 Gama 对模型大小的搜索）
  TODS-CAF(BF)                  经典 BF + LRU 负例缓存，缓存定额 = 每成员 1 bit（我们对“缓存 = adaptivity 位数”的读法）
  TODS-CAF(PLBF)                同上，但底层换成 PLBF
  SkiQF式二次准入               PLBF + LRU 缓存，比例取误报流模型的选择，同一个 key 第二次误报才写入
  纯AQF / 纯SkiQF(α=1)          只在放得下的预算下；SkiQF 版同一个 key 第二次误报才扩展指纹
  learned stacked              PLBF → 已知负例 BF → 成员 BF（保证零漏判）；已知负例 = 前 25% 查询里的误报 key；
                                缓存比例 f 与负例层每 key 位数都取事后最好（对基线有利）
参照：网格上各比例（LRU）里该负载最好的那个。

评估窗口：前 25% 查询是所有方法共同的学习期——stacked 用它离线建负例层，缓存类方法在线预热（状态延续）；
所有方法只比较后 75% 的误报率。缓存类方法的后 75% 误报 = 整条流的误报 − 前 25% 单独跑的误报（模拟是确定性的）。

用法：python src/exp10_baselines.py --dataset caida [--seeds 5]
      python src/exp10_baselines.py --report
"""

import argparse
import json
import time

import numpy as np
import pandas as pd
from numba import njit

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp4_cache_policy import simulate_policy
from exp6_split_hybrid import simulate_split
from exp7_cache_size_rule import val_entry_bits
from exp9_fp_stream_controller import (FINE, HLL_P, SKETCH_BYTES, SS_K, SETTINGS, BinMemo, FastEst, fit_stream,
                                       hll_count, hll_fill, pick_static, run_controller, space_saving_top_mass)


OUT = C.RESULTS / "exp10_baselines"
GRID = (0.0, *FINE, 0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.4, 0.6)
STACK_F = (0.02, 0.05, 0.1, 0.2, 0.4)
STACK_B2 = (2, 4, 6, 8, 12)


@njit(cache=True)
def simulate_aqf_ski(stream, reg_q, kind, h1q, h2q, space, rbits, off, mem_f, mem_h2, reserve, adapt_after):
    """纯 AQF；adapt_after=2 时同一个 key 第二次误报才扩展（SkiQF，α=1）。返回误报次数。"""
    ext = np.zeros(mem_f.size, np.int64)
    seen = np.zeros(reg_q.size, np.uint8)
    fp = 0
    for t in range(stream.size):
        x = stream[t]
        g = reg_q[x]
        if kind[g] != C.AQF:
            continue
        fx = h1q[x] % space[g]
        lo = off[g]
        hi = off[g + 1]
        j = lo + np.searchsorted(mem_f[lo:hi], fx)
        hit = False
        while j < hi and mem_f[j] == fx:
            if C.ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g]):
                hit = True
                if seen[x] + 1 >= adapt_after:
                    while (C.ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g])
                           and reserve[g] > 0 and ext[j] * rbits[g] < 64):
                        ext[j] += 1
                        reserve[g] -= 1
            j += 1
        if hit:
            fp += 1
            if seen[x] < 255:
                seen[x] += 1
    return fp


def single_bf(h1, h2, m, k):
    bits = np.zeros(max(1, m), np.uint8)
    C.bf_build(h1, h2, np.zeros(h1.size, np.int32), np.array([0, m], np.int64), np.array([m], np.int64),
               np.array([k], np.int64), bits)
    return bits


def query_bf(bits, h1, h2, m, k):
    out = np.empty(h1.size, np.bool_)
    C.bf_query(h1, h2, np.zeros(h1.size, np.int32), np.array([0, m], np.int64), np.array([m], np.int64),
               np.array([k], np.int64), bits, out)
    return out


def stacked_fpr(setup, base, kib, f, b2, stream):
    """PLBF（预算扣掉 f）→ 已知负例 BF → 成员 BF。返回整条轨迹上的 FPR；放不下返回 None。"""
    known = np.unique(stream[: stream.size // 4][base.fp_static[stream[: stream.size // 4]]])
    total = int(kib * 1024 * f) * 8
    m2 = int(b2 * max(known.size, 1))
    if known.size == 0 or m2 >= total:
        return None
    k2 = max(1, round(b2 * np.log(2)))
    l2 = single_bf(setup.h1q[known], setup.h2q[known], m2, k2)
    mem_hit = query_bf(l2, setup.h1m, setup.h2m, m2, k2)          # 成员落进负例层 → 必须进成员层
    m3 = total - m2
    n3 = int(mem_hit.sum())
    k3 = max(1, round(m3 / max(n3, 1) * np.log(2)))
    l3 = single_bf(setup.h1m[mem_hit], setup.h2m[mem_hit], m3, k3)
    in_l2 = query_bf(l2, setup.h1q, setup.h2q, m2, k2)
    l3_fp = query_bf(l3, setup.h1q, setup.h2q, m3, k3) if n3 else np.zeros(setup.h1q.size, np.bool_)
    assert query_bf(l3, setup.h1m[mem_hit], setup.h2m[mem_hit], m3, k3).all()   # 零漏判
    fp = base.fp_static & (~in_l2 | l3_fp)
    return float(fp[stream[stream.size // 4:]].mean())                 # 只算后 75%


def run(ds, seeds, budgets=None, suffix=""):
    t0 = time.time()
    setup = C.Setup(ds)
    est = FastEst(setup)
    bbar = val_entry_bits(setup)
    bins = BinMemo()
    n_pool = setup.q_score.size
    n_mem = setup.mem_score.size
    order = np.argsort(setup.q_score, kind="stable")
    if ds.endswith("_flow"):
        wls, seeds = [("真实轨迹", None)], 1
    else:
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        wls = [(w[0], w[3]) for w in workloads(pools) if w[1] != "probe-replay"]
    built = {}

    def plbf(kib, f, filt="bf", use_model=True):
        key = (kib, f, filt, use_model)
        if key not in built:
            s = C.Structure(f"{filt}{f:.3f}", filt, use_model, kib * 1024, setup, f)
            s.fp_static = s.in_pass_q | s.bf_fp_q
            built[key] = s
        return built[key]

    rows = []
    dummy = np.zeros(1, np.int64)
    for name, spec in wls:
        for seed in range(seeds):
            stream = (C.load_flow_trace(setup) if spec is None
                      else make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order))
            q = stream.size
            tail = q // 4
            qt = q - tail

            def add(kib, method, f, fpr):
                rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                             "method": method, "frac": f, "fpr": fpr})

            def tail_rate(fn):
                return (fn(stream) - fn(stream[:tail])) / qt

            def lru(kib, f, base=None):
                s = base or plbf(kib, f)
                return tail_rate(lambda st: int(simulate_policy(st, s.fp_static, s.cache_cost, s.cache_bits, 1,
                                                                dummy, np.zeros(1, np.bool_))[0]))

            for kib in budgets or budgets_of(ds):
                fits = lambda f: kib * 1024 * (1 - f) > C.N_TREES * C.TREE_BYTES
                for f in GRID:
                    if fits(f):
                        add(kib, f"网格{f:.1%}", f, lru(kib, f))
                # 我们的方法
                reserve = round(SKETCH_BYTES / (kib * 1024), 6)
                base = plbf(kib, reserve)
                fs = stream[base.fp_static[stream]]
                nr = np.zeros(1 << HLL_P, np.int64)
                fr = np.zeros(1 << HLL_P, np.int64)
                hll_fill(nr, setup.h1q[stream])
                hll_fill(fr, setup.h1q[fs])
                n_eff, D_F, QF = hll_count(nr), hll_count(fr), fs.size
                p0 = est(kib, reserve)
                W, s_F = fit_stream(QF, D_F, space_saving_top_mass(fs, SS_K)) if QF else (1.0, 0.0)
                f_ours = pick_static(est, kib, bbar, W, QF, s_F, bins, max(n_eff, W / max(p0, 1e-12)), q)
                add(kib, "误报流模型", f_ours, lru(kib, f_ours))
                fpr_c, f_c, _ = run_controller(setup, est, kib, stream, bbar, bins, base, tail_from=tail)
                add(kib, "在线控制器", f_c, fpr_c)
                # 基线
                add(kib, "PLBF(0%缓存)", 0.0, lru(kib, 0.0))
                f_tods = n_mem / (kib * 1024 * 8)
                if f_tods < 1 and fits(f_tods):
                    add(kib, "TODS-CAF(PLBF)", f_tods, lru(kib, round(f_tods, 6)))
                if f_tods < 1:
                    add(kib, "TODS-CAF(BF)", f_tods, lru(kib, None, plbf(kib, round(f_tods, 6), "bf", False)))
                s = plbf(kib, f_ours)
                add(kib, "SkiQF式二次准入", f_ours, tail_rate(lambda st: int(simulate_split(
                    st, s.reg_q, s.kind.astype(np.int64), s.bf_fp_q, s.h1q, s.h2q, s.space, s.rbits, s.aqf_off,
                    s.mem_f, s.mem_h2, s.reserve0.copy(), s.cache_bits, setup.cache_cost, False, 2)[0])))
                aqf = plbf(kib, 0.0, "aqf", False)
                if aqf.feasible:
                    for method, after in (("纯AQF", 1), ("纯SkiQF(α=1)", 2)):
                        add(kib, method, 0.0, tail_rate(lambda st: simulate_aqf_ski(
                            st, aqf.reg_q, aqf.kind.astype(np.int64), aqf.h1q, aqf.h2q, aqf.space, aqf.rbits,
                            aqf.aqf_off, aqf.mem_f, aqf.mem_h2, aqf.reserve0.copy(), after)))
                best_st = None
                for f in STACK_F:
                    if not fits(f):
                        continue
                    for b2 in STACK_B2:
                        v = stacked_fpr(setup, plbf(kib, f), kib, f, b2, stream)
                        if v is not None and (best_st is None or v < best_st[0]):
                            best_st = (v, f, b2)
                if best_st:
                    add(kib, "learned stacked(事后最优)", best_st[1], best_st[0])
        print(f"{ds} {name} done at {time.time() - t0:.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(OUT / f"rows_{ds}{suffix}.json", orient="records", force_ascii=False, indent=1)


def budgets_of(ds):
    return SETTINGS[ds]


ORDER = ["误报流模型", "在线控制器", "PLBF(0%缓存)", "TODS-CAF(PLBF)", "TODS-CAF(BF)", "SkiQF式二次准入",
         "纯AQF", "纯SkiQF(α=1)", "learned stacked(事后最优)"]


def report():
    df = pd.concat([pd.read_json(p) for p in sorted(OUT.glob("rows_*.json"))])
    a = df.groupby(["dataset", "budget_kib", "workload", "method"]).fpr.agg(["mean", "std"]).reset_index()
    best = a.groupby(["dataset", "budget_kib", "workload"])["mean"].transform("min")
    # +1 次误报的平滑（按后 75% 查询数），避免最好者为 0 时除零
    qt = {"真实轨迹": 0.75 * 5_775_801}
    eps = a.workload.map(lambda w: 1 / qt.get(w, 0.75 * 10_000_000))
    a["rel"] = (a["mean"] + eps) / (best + eps)
    a.to_json(OUT / "summary.json", orient="records", force_ascii=False, indent=1)
    lines = ["# 实验 10：与基线对比", "",
             "每格：该方法在该设置所有负载上的最坏相对代价 / 中位数（相对“网格比例与所有方法里该负载最好的那个”，"
             "分子分母各加 1 次误报平滑）。只比较后 75% 查询（前 25% 是共同学习期）。"
             "合成负载 5 个种子取均值，真实轨迹 1 次。“—”表示该预算下放不下。", "",
             "| 数据集 | 预算 | " + " | ".join(ORDER) + " |", "|---|---:|" + "---|" * len(ORDER)]
    for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=False):
        cells = []
        for m in ORDER:
            h = g[g.method == m]
            cells.append("—" if h.empty else f"{h.rel.max():.2f}× / {h.rel.median():.2f}×")
        lines.append(f"| {ds} | {kib}KiB | " + " | ".join(cells) + " |")
    # 种子间波动：我们的方法的相对标准差
    ours = a[a.method.isin(["误报流模型", "在线控制器"]) & a["std"].notna() & (a["mean"] > 0)]
    cv = (ours["std"] / ours["mean"])
    lines += ["", f"种子间波动（我们的两种方法，标准差 ÷ 均值）：中位数 {cv.median():.1%}，90 分位 {cv.quantile(0.9):.1%}。"]
    real = a[a.dataset.str.endswith("_flow")]
    lines += ["", "## 真实轨迹（绝对 FPR）", "", "| 预算 | " + " | ".join(ORDER) + " |", "|---:|" + "---:|" * len(ORDER)]
    for kib, g in real.groupby("budget_kib"):
        cells = [("—" if g[g.method == m].empty else f"{g[g.method == m]['mean'].iloc[0]:.4%}") for m in ORDER]
        lines.append(f"| {kib}KiB | " + " | ".join(cells) + " |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset")
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--budgets", help="KiB，逗号分隔；默认用 SETTINGS")
    ap.add_argument("--suffix", default="")
    args = ap.parse_args()
    if args.report:
        report()
    else:
        run(args.dataset, args.seeds, [int(b) for b in args.budgets.split(",")] if args.budgets else None, args.suffix)
