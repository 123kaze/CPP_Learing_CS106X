"""实验 6：分工型混合——放行区用缓存，backup 区用 AQF——以及缓存写入时成员比对的成本。

结构（缓存一律 LRU，比例网格同实验 4）：
  PLBF+缓存            缓存所有误报；写入时查成员索引取最短安全前缀（约 28 bit/条）
  PLBF+缓存(二次准入)   同上，但同一个 key 第二次误报才写入（SkiQF 式准入，少查成员索引）
  PLBF+缓存(64位)       存完整 64 位哈希，不查成员索引；成员被误拒的概率约 n/2^64，不是严格零漏判
  PLBF+AQF+放行区缓存    backup 换成 AQF 修自己的误报；缓存只收直接放行区的误报，前缀只需避开放行区成员
下界：纯 PLBF 加无限免费缓存（每个误报 key 只付第一次）。

“成员/反向映射查询”= 缓存写入次数（取前缀要查成员索引；64 位版本为 0）+ AQF 扩展次数（每次要查反向映射）。

用法：python src/exp6_split_hybrid.py [--seeds 5] [--dataset caida] [--budgets 128,256]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd
from numba import njit

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp4_cache_policy import FRACS, POOLS


VARIANTS = ("PLBF+缓存", "PLBF+缓存(二次准入)", "PLBF+缓存(64位)", "PLBF+AQF+放行区缓存")


@njit(cache=True)
def simulate_split(stream, reg_q, kind, bf_fp_q, h1q, h2q, space, rbits, off, mem_f, mem_h2,
                   reserve, cap, cost, pass_only, admit_after):
    """返回 [误报, 其中直接放行, 缓存命中, 缓存写入, 淘汰, AQF 扩展]。缓存为 LRU。"""
    n_pool = reg_q.size
    ext = np.zeros(mem_f.size, np.int64)
    in_cache = np.zeros(n_pool, np.uint8)
    seen_fp = np.zeros(n_pool if admit_after > 1 else 1, np.uint8)
    prv = np.full(n_pool, -1, np.int64)
    nx = np.full(n_pool, -1, np.int64)
    head = -1
    tail = -1
    used = 0
    fp = 0
    fp_pass = 0
    hits = 0
    ins = 0
    evict = 0
    adapts = 0
    for t in range(stream.size):
        x = stream[t]
        if in_cache[x]:
            hits += 1
            if x != tail:
                p, q = prv[x], nx[x]
                if p >= 0:
                    nx[p] = q
                else:
                    head = q
                prv[q] = p
                prv[x] = tail
                nx[x] = -1
                nx[tail] = x
                tail = x
            continue
        g = reg_q[x]
        kd = kind[g]
        is_fp = False
        if kd == C.PASS:
            is_fp = True
            fp_pass += 1
        elif kd == C.BF:
            is_fp = bf_fp_q[x]
        elif kd == C.AQF:
            fx = h1q[x] % space[g]
            lo = off[g]
            hi = off[g + 1]
            j = lo + np.searchsorted(mem_f[lo:hi], fx)
            while j < hi and mem_f[j] == fx:
                if C.ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g]):
                    is_fp = True
                    while (C.ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g])
                           and reserve[g] > 0 and ext[j] * rbits[g] < 64):
                        ext[j] += 1
                        reserve[g] -= 1
                        adapts += 1
                j += 1
        if not is_fp:
            continue
        fp += 1
        if pass_only and kd != C.PASS:
            continue
        c = cost[x]
        if cap <= 0 or c == 0 or c > cap:
            continue
        if admit_after > 1:
            if seen_fp[x] + 1 < admit_after:
                seen_fp[x] += 1
                continue
        in_cache[x] = 1
        used += c
        ins += 1
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
            evict += 1
    return np.array([fp, fp_pass, hits, ins, evict, adapts], np.int64)


def build(variant, kib, frac, setup):
    filt = "aqf" if "AQF" in variant else "bf"
    s = C.Structure(f"{variant}{frac:.0%}", filt, True, kib * 1024, setup, frac)
    s.variant = variant
    s.pass_only = variant == "PLBF+AQF+放行区缓存"
    s.admit_after = 2 if "二次准入" in variant else 1
    if "64位" in variant:
        s.cost = np.full(setup.h1q.size, 64, np.int64)
    elif s.pass_only:
        reg_m = np.searchsorted(s.cuts, setup.mem_score, side="right")
        pass_h1 = np.sort(setup.h1m[s.kind[reg_m] == C.PASS])
        s.cost = np.zeros(setup.h1q.size, np.int64)
        C.cache_entry_bits(pass_h1, setup.h1q, s.in_pass_q, s.cost)
    else:
        s.cost = setup.cache_cost
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--dataset", default="caida")
    ap.add_argument("--budgets", default="128,256")
    ap.add_argument("--out", default="exp6_split_hybrid")
    args = ap.parse_args()
    budgets = [int(b) for b in args.budgets.split(",")]
    out = C.RESULTS / args.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setup = C.Setup(args.dataset)
    n_pool = setup.q_score.size
    score_order = np.argsort(setup.q_score, kind="stable")

    structs, base = [], {}
    for kib in budgets:
        base[kib] = C.Structure("PLBF", "bf", True, kib * 1024, setup)
        for variant in VARIANTS:
            for f in FRACS:
                if kib * 1024 * (1 - f) <= C.N_TREES * C.TREE_BYTES:
                    continue
                if f == 0 and variant != VARIANTS[0] and variant != VARIANTS[3]:
                    continue                             # 0% 缓存时前三种相同
                structs.append(build(variant, kib, f, setup))
    print(f"{len(structs)} structures ready at {time.time() - t0:.1f}s")

    rows = []
    for name, family, pool, spec, _ in [w for w in workloads(POOLS) if w[1] != "probe-replay"]:
        for seed in range(args.seeds):
            stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), score_order)
            seen = np.bincount(stream, minlength=n_pool) > 0
            q = stream.size
            bound = {kib: int((seen & (b.in_pass_q | b.bf_fp_q)).sum()) / q for kib, b in base.items()}
            for s in structs:
                res = simulate_split(stream, s.reg_q, s.kind.astype(np.int64), s.bf_fp_q, s.h1q, s.h2q,
                                     s.space, s.rbits, s.aqf_off, s.mem_f, s.mem_h2, s.reserve0.copy(),
                                     s.cache_bits, s.cost, s.pass_only, s.admit_after)
                fp, fp_pass, hits, ins, evict, adapts = (int(v) for v in res)
                lookups = (0 if "64位" in s.variant else ins) + adapts
                rows.append({"budget_kib": s.budget_kib, "variant": s.variant, "cache_frac": s.cache_frac,
                             "workload": name, "family": family, "pool": pool, "seed": seed, "queries": q,
                             "fpr": fp / q, "fp": fp, "fp_pass": fp_pass, "hits": hits, "inserts": ins,
                             "evictions": evict, "adaptations": adapts, "member_lookups": lookups,
                             "bound_fpr": bound[s.budget_kib]})
        print(f"{name} done at {time.time() - t0:.1f}s")

    df = pd.DataFrame(rows)
    meta = {"dataset": args.dataset, "budgets_kib": budgets, "seeds": args.seeds,
            "structures": [dict(s.summary(), variant=s.variant) for s in structs]}
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    report(df, meta, out)
    print(f"total {time.time() - t0:.1f}s")


def report(df, meta, out):
    a = df.groupby(["budget_kib", "workload", "variant", "cache_frac"], sort=False).agg(
        fpr=("fpr", "mean"), lookups=("member_lookups", "mean"), bound=("bound_fpr", "mean"),
        q=("queries", "mean"))
    lines = [f"# 实验 6：分工型混合与成员比对成本（{meta['dataset']}）", "",
             f"{meta['seeds']} 个种子取均值，缓存一律 LRU。每格写“该结构在比例网格上最好的 FPR（比例）”，"
             "以及在那个比例下每 100 万次查询的成员/反向映射查询次数。下界 = 纯 PLBF 加无限免费缓存。", ""]
    best_rows = []
    for kib in meta["budgets_kib"]:
        lines += [f"## {kib}KiB", "",
                  "| 负载 | 下界 | " + " | ".join(VARIANTS) + " |", "|---|---:|" + "---:|" * len(VARIANTS)]
        for wl in dict.fromkeys(df.workload):
            cells = []
            b = a.loc[(kib, wl)].bound.iloc[0]
            for v in VARIANTS:
                g = a.loc[(kib, wl, v)]
                f = g.fpr.idxmin()
                r = g.loc[f]
                cells.append(f"{r.fpr:.4%}（{f:.0%}，{r.lookups / r.q * 1e6:,.0f}）")
                best_rows.append({"budget_kib": kib, "workload": wl, "variant": v, "best_frac": f,
                                  "best_fpr": r.fpr, "bound": b, "lookups_per_m": r.lookups / r.q * 1e6})
            lines.append(f"| {wl} | {b:.4%} | " + " | ".join(cells) + " |")
    s = pd.DataFrame(best_rows)
    s["gap"] = s.best_fpr / s.bound.where(s.bound > 0)
    lines += ["", "## 离下界多远（各自最优比例下的 FPR ÷ 下界）", "",
              "| 预算 | 结构 | 中位数 | 最差 | 最差负载 | 下界 2 倍以外的负载数 |", "|---:|---|---:|---:|---|---:|"]
    for (kib, v), g in s.groupby(["budget_kib", "variant"], sort=False):
        g = g.dropna(subset=["gap"])
        lines.append(f"| {kib}KiB | {v} | {g.gap.median():.2f}× | {g.gap.max():.2f}× | "
                     f"{g.loc[g.gap.idxmax(), 'workload']} | {(g.gap > 2).sum()} |")
    ref = s[s.variant == "PLBF+缓存"].set_index(["budget_kib", "workload"]).best_fpr
    lines += ["", "## 分工型混合相对 PLBF+缓存（各自最优比例；<1 表示分工型更好）", "",
              "| 预算 | 中位数 | 最好 | 最好的负载 | 最差 | 最差的负载 |", "|---:|---:|---:|---|---:|---|"]
    h = s[s.variant == "PLBF+AQF+放行区缓存"].set_index(["budget_kib", "workload"])
    ratio = (h.best_fpr / ref.where(ref > 0)).dropna()
    for kib, r in ratio.groupby(level=0):
        r = r.droplevel(0)
        lines.append(f"| {kib}KiB | {r.median():.2f} | {r.min():.2f} | {r.idxmin()} | {r.max():.2f} | {r.idxmax()} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    s.to_json(out / "summary.json", orient="records", force_ascii=False, indent=1)


if __name__ == "__main__":
    main()
