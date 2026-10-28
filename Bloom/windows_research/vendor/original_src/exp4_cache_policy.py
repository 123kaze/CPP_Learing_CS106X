"""实验 4：工作集远大于缓存时，离下界的差距来自比例、容量还是淘汰策略。

在 Caida 128/256KiB 下，对每个缓存比例（补到 60%/80%）比较四种缓存策略：
  FIFO        实验 3 用的策略（回归对照：结果与实验 3 逐行一致）
  LRU
  oracle-LFU  事先知道整条轨迹，只准入总出现次数最多的那批误报 key，填满容量为止，进了不淘汰
  OPT         Bélády：淘汰下次出现最晚的 key，新 key 若最晚出现则直接不收（条目长度只差几 bit，按条近似最优）
下界仍是无限免费缓存：每个误报 key 只付第一次。

基础结构都是静态 PLBF，所以每个 key 是否误报是固定的；探测重放负载的查询依赖过滤器输出，
OPT 无从定义，这里不跑。

用法：python src/exp4_cache_policy.py [--seeds 5] [--dataset caida] [--budgets 128,256]
"""

import argparse
import json
import time

import numpy as np
import pandas as pd
from numba import njit

import common as C
from exp2_repetition_cache import make_stream, workloads


FRACS = (0.0, 0.01, 0.02, 0.05, 0.10, 0.20, 0.40, 0.60, 0.80)
POLICIES = {0: "FIFO", 1: "LRU", 2: "oracle-LFU", 3: "OPT"}
POOLS = {"1万": 10_000, "10万": 100_000, "100万": 1_000_000, "全部": None}
NEVER = np.iinfo(np.int64).max


@njit(cache=True)
def next_occurrence(stream, n_pool):
    nxt = np.empty(stream.size, np.int64)
    last = np.full(n_pool, NEVER, np.int64)
    for t in range(stream.size - 1, -1, -1):
        nxt[t] = last[stream[t]]
        last[stream[t]] = t
    return nxt


@njit(cache=True)
def heap_swap(hk, hv, pos, i, j):
    hk[i], hk[j] = hk[j], hk[i]
    hv[i], hv[j] = hv[j], hv[i]
    pos[hk[i]] = i
    pos[hk[j]] = j


@njit(cache=True)
def heap_up(hk, hv, pos, i):
    while i > 0:
        p = (i - 1) >> 1
        if hv[p] >= hv[i]:
            break
        heap_swap(hk, hv, pos, i, p)
        i = p


@njit(cache=True)
def heap_down(hk, hv, pos, i, size):
    while True:
        l = 2 * i + 1
        if l >= size:
            break
        c = l
        if l + 1 < size and hv[l + 1] > hv[l]:
            c = l + 1
        if hv[i] >= hv[c]:
            break
        heap_swap(hk, hv, pos, i, c)
        i = c


@njit(cache=True)
def simulate_policy(stream, fp_static, cost, cap, policy, nxt, admit):
    """返回 [误报次数, 缓存命中, 插入次数, 淘汰次数]。只有静态误报 key 会和缓存打交道。"""
    n_pool = fp_static.size
    in_cache = np.zeros(n_pool, np.uint8)
    used = 0
    fp = 0
    hits = 0
    ins = 0
    evict = 0
    # FIFO：环形队列；LRU：双向链表（head 最旧）；OPT：按下次出现时间的索引最大堆
    fifo = np.empty(n_pool, np.int64)
    fh = 0
    ft = 0
    prv = np.full(n_pool if policy == 1 else 1, -1, np.int64)
    nx = np.full(n_pool if policy == 1 else 1, -1, np.int64)
    lru_head = -1
    lru_tail = -1
    hk = np.empty(n_pool if policy == 3 else 1, np.int64)
    hv = np.empty(n_pool if policy == 3 else 1, np.int64)
    pos = np.full(n_pool if policy == 3 else 1, -1, np.int64)
    hsize = 0
    for t in range(stream.size):
        x = stream[t]
        if not fp_static[x]:
            continue
        if in_cache[x]:
            hits += 1
            if policy == 1 and x != lru_tail:          # 移到最近端
                p, q = prv[x], nx[x]
                if p >= 0:
                    nx[p] = q
                else:
                    lru_head = q
                prv[q] = p
                prv[x] = lru_tail
                nx[x] = -1
                nx[lru_tail] = x
                lru_tail = x
            elif policy == 3:
                hv[pos[x]] = nxt[t]
                heap_up(hk, hv, pos, pos[x])
                heap_down(hk, hv, pos, pos[x], hsize)
            continue
        fp += 1
        c = cost[x]
        if cap <= 0 or c == 0 or c > cap:
            continue
        if policy == 2:                                # oracle-LFU：只收选定集合，永不淘汰
            if admit[x]:
                in_cache[x] = 1
                ins += 1
            continue
        if policy == 3 and nxt[t] == NEVER:            # OPT：以后不再出现的 key 不收
            continue
        in_cache[x] = 1
        used += c
        ins += 1
        if policy == 0:
            fifo[ft] = x
            ft += 1
            if ft == n_pool:
                ft = 0
        elif policy == 1:
            prv[x] = lru_tail
            nx[x] = -1
            if lru_tail >= 0:
                nx[lru_tail] = x
            else:
                lru_head = x
            lru_tail = x
        else:
            hk[hsize] = x
            hv[hsize] = nxt[t]
            pos[x] = hsize
            hsize += 1
            heap_up(hk, hv, pos, hsize - 1)
        while used > cap:
            if policy == 0:
                y = fifo[fh]
                fh += 1
                if fh == n_pool:
                    fh = 0
            elif policy == 1:
                y = lru_head
                lru_head = nx[y]
                if lru_head >= 0:
                    prv[lru_head] = -1
                else:
                    lru_tail = -1
            else:
                y = hk[0]
                hsize -= 1
                heap_swap(hk, hv, pos, 0, hsize)
                heap_down(hk, hv, pos, 0, hsize)
                pos[y] = -1
            in_cache[y] = 0
            used -= cost[y]
            evict += 1
    return np.array([fp, hits, ins, evict], np.int64)


def oracle_admit(cnt, fp_static, cost, cap, n_pool):
    """出现次数 ≥2 的误报 key 按总次数从高到低装满容量。"""
    cand = np.flatnonzero(fp_static & (cnt >= 2) & (cost > 0))
    cand = cand[np.argsort(-cnt[cand], kind="stable")]
    take = cand[np.cumsum(cost[cand]) <= cap]
    admit = np.zeros(n_pool, np.bool_)
    admit[take] = True
    return admit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=5)
    ap.add_argument("--dataset", default="caida")
    ap.add_argument("--budgets", default="128,256")
    ap.add_argument("--out", default="exp4_cache_policy")
    args = ap.parse_args()
    budgets = [int(b) for b in args.budgets.split(",")]
    out = C.RESULTS / args.out
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    setup = C.Setup(args.dataset)
    n_pool = setup.q_score.size
    score_order = np.argsort(setup.q_score, kind="stable")

    structs = []
    for kib in budgets:
        for f in FRACS:
            if kib * 1024 * (1 - f) <= C.N_TREES * C.TREE_BYTES:
                continue                                 # 剩下的预算放不下模型
            s = C.Structure(f"PLBF+缓存{f:.0%}", "bf", True, kib * 1024, setup, f)
            s.fp_static = s.in_pass_q | s.bf_fp_q
            structs.append(s)
    print(f"{len(structs)} structures ready at {time.time() - t0:.1f}s")

    rows = []
    wls = [w for w in workloads(POOLS) if w[1] != "probe-replay"]
    for name, family, pool, spec, _ in wls:
        for seed in range(args.seeds):
            stream = make_stream(spec, n_pool, np.random.default_rng(2000 + seed), score_order)
            nxt = next_occurrence(stream, n_pool)
            cnt = np.bincount(stream, minlength=n_pool)
            seen = cnt > 0
            q = stream.size
            for s in structs:
                d_f = int((seen & s.fp_static).sum())
                base = {"budget_kib": s.budget_kib, "cache_frac": s.cache_frac, "workload": name,
                        "family": family, "pool": pool, "seed": seed, "queries": q,
                        "bound_fpr": d_f / q, "d_f": d_f, "q_f": int(cnt[s.fp_static].sum())}
                for pid, pname in POLICIES.items():
                    if s.cache_bits == 0 and pid > 0:
                        continue                         # 0% 缓存时四种策略相同
                    admit = (oracle_admit(cnt, s.fp_static, s.cache_cost, s.cache_bits, n_pool)
                             if pid == 2 else np.zeros(1, np.bool_))
                    res = simulate_policy(stream, s.fp_static, s.cache_cost, s.cache_bits, pid, nxt, admit)
                    for p2 in ([pid] if s.cache_bits else POLICIES):
                        rows.append(dict(base, policy=POLICIES[p2], fpr=int(res[0]) / q, fp=int(res[0]),
                                         hits=int(res[1]), inserts=int(res[2]), evictions=int(res[3])))
        print(f"{name} done at {time.time() - t0:.1f}s")

    df = pd.DataFrame(rows)
    meta = {"dataset": args.dataset, "budgets_kib": budgets, "fracs": [s.cache_frac for s in structs],
            "seeds": args.seeds, "structures": [s.summary() for s in structs]}
    (out / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    (out / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    report(df, meta, out)
    print(f"total {time.time() - t0:.1f}s")


def report(df, meta, out):
    a = df.groupby(["budget_kib", "workload", "policy", "cache_frac"], sort=False).fpr.mean()
    # 无限免费缓存的下界只取决于基础 PLBF（比例 0）的误报集合
    bound = (df[df.cache_frac == 0].groupby(["budget_kib", "workload"], sort=False).bound_fpr.mean())
    lines = [f"# 实验 4：差距来自比例、容量还是淘汰策略（{meta['dataset']}）", "",
             f"{meta['seeds']} 个种子取均值。下界 = 纯 PLBF 加无限免费缓存（每个误报 key 只付第一次）。"
             "“最优比例”是该策略在比例网格上 FPR 最低的那一档。", ""]
    summary = []
    for kib in meta["budgets_kib"]:
        lines += [f"## {kib}KiB", "",
                  "| 负载 | 下界 | " + " | ".join(f"{p} 最优 FPR（比例）" for p in POLICIES.values()) + " |",
                  "|---|---:|" + "---:|" * len(POLICIES)]
        for wl in dict.fromkeys(df.workload):
            b = bound.loc[(kib, wl)]
            cells = []
            for p in POLICIES.values():
                curve = a.loc[(kib, wl, p)]
                f = curve.idxmin()
                cells.append(f"{curve.min():.4%}（{f:.0%}）")
                summary.append({"budget_kib": kib, "workload": wl, "policy": p, "best_fpr": curve.min(),
                                "best_frac": f, "bound": b})
            lines.append(f"| {wl} | {b:.4%} | " + " | ".join(cells) + " |")
    s = pd.DataFrame(summary)
    s["gap"] = s.best_fpr / s.bound.where(s.bound > 0)
    lines += ["", "## 各策略在最优比例下离下界多远（最优 FPR ÷ 下界）", "",
              "| 预算 | 策略 | 中位数 | 最差 | 最差负载 | 最优比例的取值 |", "|---:|---|---:|---:|---|---|"]
    for (kib, p), g in s.groupby(["budget_kib", "policy"], sort=False):
        g = g.dropna(subset=["gap"])
        lines.append(f"| {kib}KiB | {p} | {g.gap.median():.2f}× | {g.gap.max():.2f}× | "
                     f"{g.loc[g.gap.idxmax(), 'workload']} | "
                     f"{', '.join(f'{v:.0%}' for v in sorted(g.best_frac.unique()))} |")
    lines += ["", "## 固定比例的代价（同一策略内：固定比例 FPR ÷ 该负载最优比例 FPR）", "",
              "| 预算 | 策略 | 最好的固定比例 | 它的最差代价 | 最差负载 |", "|---:|---|---:|---:|---|"]
    for kib in meta["budgets_kib"]:
        for p in POLICIES.values():
            piv = a.loc[kib].xs(p, level="policy").unstack("cache_frac")
            best = piv.min(axis=1)
            reg = piv.div(best.where(best > 0), axis=0).fillna(1.0)
            worst = reg.max()
            f = worst.idxmin()
            lines.append(f"| {kib}KiB | {p} | {f:.0%} | {worst.min():.2f}× | {reg[f].idxmax()} |")
    (out / "report.md").write_text("\n".join(lines) + "\n")
    s.to_json(out / "summary.json", orient="records", force_ascii=False, indent=1)


if __name__ == "__main__":
    main()
