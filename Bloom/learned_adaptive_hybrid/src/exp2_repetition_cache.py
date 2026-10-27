"""实验 2：重复程度 × 负例缓存。

结构（256KiB、1MiB）：
  PLBF                 纯 PLBF（缓存 0%）
  PLBF+缓存1/2/5/10/20%  负例缓存从同一预算里扣，剩余预算重新给 PLBF 分配
  PLBF+AQF             朴素混合
  PLBF+无限免费缓存     纯 PLBF 的分配，加一个无限大、不占预算的缓存：每个误报 key 只付第一次，
                       是任何"误报反馈后修正"方案在该分配下的下界

负例缓存挡在整个结构前面：每次误报（直接放行或 backup）都把该 key 记下（FIFO 淘汰），之后
被缓存拒绝。每条记录取与全部成员都不冲突的最短 h1 前缀，再加 6 bit 长度字段，按这个位数从
缓存容量里扣。模拟时按 key 身份判断命中，忽略了前缀碰巧挡住别的非成员的小额收益。

负载按重复程度扫描：查询池 1 万 / 10 万 / 全部测试负例 × {uniform, Zipf 0.8 / 1.1 / 1.5}，
另有每 key 只查一次、全新对抗（按模型分数从高到低，每 key 一次）、向难负例漂移（第 t 条查询以
0.5·t/Q 的概率来自模型分数最高的 2 万个测试负例，否则来自全部测试负例）、探测重放 10%。
横轴 D_H/Q_H 以纯 PLBF 的直接放行区 H 为准，所有结构共用。

用法：python src/exp2_repetition_cache.py [--seeds 5]
实验 3（Caida，误报工作集远大于缓存）复用本脚本：
  python src/exp2_repetition_cache.py --dataset caida --budgets 128,256,1024 \
      --fracs 0.01,0.02,0.05,0.1,0.2,0.4 --pools 1万=10000,10万=100000,100万=1000000,全部= \
      --out exp3_caida_working_set --title "实验 3：Caida 上的重复程度 × 负例缓存"
"""

import argparse
import json
import time

import numpy as np
import pandas as pd

import common as C


QUERIES = 10_000_000
ZIPFS = (0.8, 1.1, 1.5)
FRESH_ADV_K = 50_000
HARD_TOP = 20_000


def workloads(pools):
    """(名称, 族, 查询池, 生成参数, 对抗概率)。"""
    out = []
    for pool_name, size in pools.items():
        out.append((f"uniform-{pool_name}", "uniform", pool_name, ("uniform", size), 0.0))
        for a in ZIPFS:
            out.append((f"zipf{a}-{pool_name}", f"zipf{a}", pool_name, ("zipf", size, a), 0.0))
    out.append(("每key一次", "once", "全部", ("once",), 0.0))
    out.append(("全新对抗", "fresh-adv", "全部", ("fresh",), 0.0))
    out.append(("向难负例漂移", "hard-drift", "全部", ("hard-drift",), 0.0))
    out.append(("探测重放10%", "probe-replay", "全部", ("uniform", None), 0.10))
    return out


def make_stream(spec, n_pool, rng, score_order):
    kind = spec[0]
    if kind == "once":
        return rng.permutation(n_pool)
    if kind == "fresh":
        return score_order[::-1][:FRESH_ADV_K].copy()
    if kind == "hard-drift":
        hard = rng.random(QUERIES) < 0.5 * np.arange(QUERIES) / QUERIES
        out = rng.integers(0, n_pool, QUERIES)
        out[hard] = score_order[n_pool - HARD_TOP + rng.integers(0, HARD_TOP, int(hard.sum()))]
        return out
    size = spec[1] or n_pool
    subset = rng.choice(n_pool, size, replace=False) if size < n_pool else np.arange(n_pool)
    if kind == "uniform":
        return subset[rng.integers(0, size, QUERIES)]
    cdf = np.cumsum(np.arange(1, size + 1, dtype=np.float64) ** -spec[2])
    ranks = np.minimum(np.searchsorted(cdf / cdf[-1], rng.random(QUERIES)), size - 1)
    return subset[rng.permutation(size)[ranks]]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--dataset", default="cod")
    ap.add_argument("--budgets", default="256,1024", help="KiB，逗号分隔")
    ap.add_argument("--fracs", default="0.01,0.02,0.05,0.1,0.2", help="缓存占预算的比例")
    ap.add_argument("--pools", default="1万=10000,10万=100000,全部=", help="名称=大小，空表示全部测试负例")
    ap.add_argument("--out", default="exp2_repetition_cache")
    ap.add_argument("--title", default="实验 2：重复程度 × 负例缓存")
    args = ap.parse_args()
    budgets = [int(b) for b in args.budgets.split(",")]
    fracs = [float(f) for f in args.fracs.split(",")]
    pools = {k: (int(v) if v else None) for k, v in (p.split("=") for p in args.pools.split(","))}
    out = C.RESULTS / args.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setup = C.Setup(args.dataset)
    n_pool = setup.q_score.size
    score_order = np.argsort(setup.q_score, kind="stable")

    structures, ref_h = [], {}
    for kib in budgets:
        plbf = C.Structure("PLBF", "bf", True, kib * 1024, setup)
        ref_h[kib] = plbf.in_pass_q
        structures.append(plbf)
        for frac in fracs:
            structures.append(C.Structure(f"PLBF+缓存{frac:.0%}", "bf", True, kib * 1024, setup, frac))
        structures.append(C.Structure("PLBF+AQF", "aqf", True, kib * 1024, setup))
        structures.append(C.Structure("PLBF+无限免费缓存", "bf", True, kib * 1024, setup,
                                      free_cache=True))
    for s in structures:
        info = s.summary()
        print(f"{s.budget_kib:>5}KiB {s.name:<12} cache={info['cache_bytes']}B "
              f"filter={info['filter_bytes']}B est_val_fpr={info['est_val_fpr']:.4%} "
              f"H区测试key={info['test_keys_in_pass']}")

    rows = []
    for name, family, pool, spec, adv_p in workloads(pools):
        for seed in range(args.seeds):
            stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), score_order)
            for s in structures:
                res, _ = s.run(stream, adv_p, 11 + seed, ref_h[s.budget_kib])
                q = stream.size
                fp_pass, fp_filter = int(res[C.FP_PASS]), int(res[C.FP_FILTER])
                rows.append({
                    "budget_kib": s.budget_kib, "structure": s.name, "cache_frac": s.cache_frac,
                    "workload": name, "family": family, "pool": pool, "seed": seed, "queries": q,
                    "fpr": (fp_pass + fp_filter) / q, "fpr_filter_only": fp_filter / q,
                    "fp_pass": fp_pass, "fp_filter": fp_filter,
                    "q_h": int(res[C.Q_H]), "d_h": int(res[C.D_H]),
                    "rep": int(res[C.D_H]) / max(1, int(res[C.Q_H])),
                    "cache_hits": int(res[C.C_HITS]), "cache_inserts": int(res[C.C_INS]),
                    "cache_entry_bits": int(res[C.C_INS_BITS]) / max(1, int(res[C.C_INS])),
                    "cache_evictions": int(res[C.C_EVICT]), "adaptations": int(res[C.ADAPTS]),
                })
        print(f"{name} done at {time.time() - t0:.1f}s")

    df = pd.DataFrame(rows)

    meta = {"title": args.title, "dataset": args.dataset, "structures": [s.summary() for s in structures],
            "seeds": args.seeds, "queries": QUERIES, "pool_size": n_pool, "fresh_adv_k": FRESH_ADV_K,
            "hard_top": HARD_TOP, "budgets_kib": budgets, "cache_fracs": fracs, "len_bits": C.LEN_BITS}
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    report(df, meta, out)
    print(f"total {time.time() - t0:.1f}s")


def report(df, meta, out):
    frac_names = {0: "PLBF", **{round(f * 100): f"PLBF+缓存{f:.0%}" for f in meta["cache_fracs"]}}
    order = [*frac_names.values(), "PLBF+AQF", "PLBF+无限免费缓存"]
    agg = (df.groupby(["budget_kib", "workload", "structure"], sort=False)
             .agg(fpr=("fpr", "mean"), rep=("rep", "mean"), d_h=("d_h", "mean"), q_h=("q_h", "mean"),
                  entry_bits=("cache_entry_bits", "mean"), evict=("cache_evictions", "mean"))
             .reset_index())
    wls = list(dict.fromkeys(df.workload))
    lines = [f"# {meta['title']}", "",
             f"数据集 {meta['dataset']}。{meta['seeds']} 个种子取均值。重复型负载每次 {meta['queries']:,} 条查询；"
             f"“每key一次”查询全部 {meta['pool_size']:,} 个测试 key 各一次；“全新对抗”按模型分数从高到低取前 "
             f"{meta['fresh_adv_k']:,} 个，各查一次。D_H、Q_H 以纯 PLBF 的直接放行区为准。", ""]
    lines += ["## 结构配置", "", "| 预算 | 结构 | 缓存B | 过滤器B | 验证集估计FPR | 直接放行段数 | H 区测试 key |",
              "|---:|---|---:|---:|---:|---:|---:|"]
    for s in meta["structures"]:
        cache = "无限，不计" if s["cache_bytes"] < 0 else f"{s['cache_bytes']:,}"
        lines.append(f"| {s['budget_kib']}KiB | {s['name']} | {cache} | {s['filter_bytes']:,} | "
                     f"{s['est_val_fpr']:.4%} | {s['pass_regions']} | {s['test_keys_in_pass']:,} |")

    for kib in meta["budgets_kib"]:
        a = agg[agg.budget_kib == kib]
        lines += ["", f"## {kib}KiB：FPR", "",
                  "| 负载 | D_H | Q_H | D_H/Q_H | " + " | ".join(order) + " | 最优缓存比例 |",
                  "|---|---:|---:|---:|" + "---:|" * len(order) + "---|"]
        for wl in wls:
            g = a[a.workload == wl].set_index("structure")
            ref = g.loc["PLBF"]
            cached = {f: g.loc[n, "fpr"] for f, n in frac_names.items()}
            best = min(cached, key=cached.get)
            cells = [f"{g.loc[n, 'fpr']:.4%}" for n in order]
            lines.append(f"| {wl} | {ref.d_h:,.0f} | {ref.q_h:,.0f} | {ref.rep:.4f} | "
                         + " | ".join(cells) + f" | {best}% |")
        bits = a[a.structure.isin(list(frac_names.values())[1:]) & (a.entry_bits > 0)].entry_bits
        lines += ["", f"负例缓存每条记录平均 {bits.mean():.1f} bit（含 {meta['len_bits']} bit 长度字段），"
                      f"范围 {bits.min():.1f}–{bits.max():.1f}。"]

        # 固定比例相对于各负载最优比例的代价
        lines += ["", f"### {kib}KiB：固定缓存比例的代价（FPR / 该负载下各比例中最好的 FPR）", "",
                  "| 固定比例 | 中位数 | 最坏 | 最坏出现在 |", "|---:|---:|---:|---|"]
        piv = a[a.structure.isin(frac_names.values())].pivot(index="workload", columns="structure", values="fpr")
        best = piv.min(axis=1)
        for f, n in frac_names.items():
            ratio = (piv[n] / best.where(best > 0)).fillna(1.0)
            ratio[(piv[n] == 0) & (best == 0)] = 1.0
            lines.append(f"| {f}% | {ratio.median():.2f}× | {ratio.max():.2f}× | {ratio.idxmax()} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
