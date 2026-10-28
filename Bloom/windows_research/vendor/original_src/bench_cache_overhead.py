"""负例缓存的查询开销：缓存 → 模型 → PLBF 与 模型 → PLBF 的每查询耗时（单线程，numba）。

部件：
  模型     48 树 LightGBM 的原生遍历（从 dump_model 导出，结果与 booster.predict 逐条核对）
  PLBF     按分数找分段 + 该段 BF 的 k 次探测
  缓存     开放寻址表：桶号取 h1 高 b 位，每格存 h1 与前缀长度 L，命中条件是高 L 位相同

缓存里装的是实验 2 在“均匀，全部测试负例”负载上实际插入过的误报 key（容量按预算 10%）。
只测耗时；内存仍按实验里每条 L+6 bit 记账（相当于满载的商表），真实哈希表另有负载余量。

用法：python src/bench_cache_overhead.py [--dataset cod]
"""

import argparse
import json
import time

import lightgbm as lgb
import numpy as np
from numba import njit

import common as C


def export_trees(booster):
    """把 LightGBM 树展平成数组；节点编号：内部节点 >= 0，叶子用 ~leaf_index。"""
    trees = booster.dump_model()["tree_info"]
    feat, thr, left, right, leaf_val, root = [], [], [], [], [], []
    for t in trees:
        def walk(node):
            if "leaf_index" in node:
                leaf_val.append(node["leaf_value"])
                return ~(len(leaf_val) - 1)
            assert node["decision_type"] == "<="   # 特征全是有限数值，不涉及缺失值分支
            idx = len(feat)
            feat.append(node["split_feature"])
            thr.append(node["threshold"])
            left.append(0)
            right.append(0)
            left[idx] = walk(node["left_child"])
            right[idx] = walk(node["right_child"])
            return idx

        root.append(walk(t["tree_structure"]))
    return (np.array(feat, np.int64), np.array(thr, np.float64), np.array(left, np.int64),
            np.array(right, np.int64), np.array(leaf_val, np.float64), np.array(root, np.int64))


@njit(cache=True)
def model_score(x, feat, thr, left, right, leaf_val, root):
    s = 0.0
    for t in range(root.size):
        n = root[t]
        while n >= 0:
            n = left[n] if x[feat[n]] <= thr[n] else right[n]
        s += leaf_val[~n]
    return s


@njit(cache=True)
def cache_lookup(h, table_h, table_len, bits):
    i = np.int64(h >> np.uint64(64 - bits))
    mask = (1 << bits) - 1
    while table_len[i] != 0:
        L = table_len[i]
        if ((h ^ table_h[i]) >> np.uint64(64 - L)) == 0:
            return True
        i = (i + 1) & mask
    return False


@njit(cache=True)
def plbf_query(score, h1, cuts, kind, off, m, k, bits):
    g = np.searchsorted(cuts, score, side="right")
    kd = kind[g]
    if kd == C.PASS:
        return True
    if kd != C.BF:
        return False
    for j in range(k[g]):
        if bits[off[g] + C.bf_pos(h1, j, m[g])] == 0:
            return False
    return True


@njit(cache=True)
def run_pipeline(X, H1, feat, thr, left, right, leaf_val, root, cuts, kind, off, m, k, bits,
                 table_h, table_len, tbits, mode):
    """mode 0：只算模型；1：模型+PLBF；2：只查缓存；3：缓存→模型→PLBF。返回接受数（防止被优化掉）。"""
    acc = 0
    for i in range(H1.size):
        if mode == 2:
            acc += cache_lookup(H1[i], table_h, table_len, tbits)
            continue
        if mode == 3 and cache_lookup(H1[i], table_h, table_len, tbits):
            continue
        s = model_score(X[i], feat, thr, left, right, leaf_val, root)
        if mode == 0:
            acc += s > 0
        else:
            acc += plbf_query(s, H1[i], cuts, kind, off, m, k, bits)
    return acc


def build_table(keys, lens):
    tbits = int(np.ceil(np.log2(max(2, keys.size) / 0.7)))   # 负载 ≤ 0.7
    assert lens.min() >= tbits, "前缀短于桶号位数，需要更小的表"
    table_h = np.zeros(1 << tbits, np.uint64)
    table_len = np.zeros(1 << tbits, np.int64)
    mask = (1 << tbits) - 1
    for h, L in zip(keys, lens):
        i = int(h >> np.uint64(64 - tbits))
        while table_len[i]:
            i = (i + 1) & mask
        table_h[i], table_len[i] = h, L
    return table_h, table_len, tbits


def timeit(fn, reps=7):
    fn()
    best = float("inf")
    for _ in range(reps):
        t0 = time.perf_counter()
        fn()
        best = min(best, time.perf_counter() - t0)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="cod")
    ap.add_argument("--budget-kib", type=int, default=256)
    ap.add_argument("--frac", type=float, default=0.10)
    args = ap.parse_args()
    out = C.RESULTS / "bench_cache_overhead"
    out.mkdir(parents=True, exist_ok=True)

    setup = C.Setup(args.dataset)
    ids, y, X, _ = C.load_dataset(args.dataset)
    booster = lgb.Booster(model_file=str(C.CACHE / args.dataset / "model48.txt"))
    tree = export_trees(booster)
    test = setup.split["neg_test"]
    Xq = np.ascontiguousarray(X[test].astype(np.float64))
    n = min(1_000_000, Xq.shape[0])
    Xq, H1 = Xq[:n], setup.h1q[:n]

    # 核对：原生遍历与 LightGBM 输出一致
    sample = np.arange(0, n, max(1, n // 20000))
    ours = np.array([model_score(Xq[i], *tree) for i in sample])
    ref = booster.predict(Xq[sample], raw_score=True)
    assert np.allclose(ours, ref, atol=1e-6), np.abs(ours - ref).max()

    s = C.Structure("PLBF+缓存", "bf", True, args.budget_kib * 1024, setup, args.frac)
    # 用一次真实运行把缓存填满：均匀查询全部测试负例，记录最后留在缓存里的 key
    stream = np.random.default_rng(0).integers(0, setup.h1q.size, 10_000_000)
    fp = np.zeros(setup.h1q.size, np.bool_)
    fp[s.in_pass_q | s.bf_fp_q] = True
    hits = np.unique(stream[fp[stream]])
    budget_bits = s.cache_bits
    keys, lens, used = [], [], 0
    for x in hits[np.random.default_rng(1).permutation(hits.size)]:   # 随机取一批，装到容量为止
        c = int(setup.cache_cost[x])
        if c == 0 or used + c > budget_bits:
            continue
        keys.append(setup.h1q[x])
        lens.append(c - C.LEN_BITS)
        used += c
    table_h, table_len, tbits = build_table(np.array(keys, np.uint64), np.array(lens, np.int64))

    args_common = (Xq, H1, *tree, s.cuts, s.kind.astype(np.int64), s.bf_off, s.m, s.k, s.bits,
                   table_h, table_len, tbits)
    t = {mode: timeit(lambda mode=mode: run_pipeline(*args_common, mode)) / n * 1e9 for mode in range(4)}
    t_lgb = timeit(lambda: booster.predict(Xq[:200_000], raw_score=True, num_threads=1), reps=3) / 200_000 * 1e9
    res = {
        "dataset": args.dataset, "budget_kib": args.budget_kib, "cache_frac": args.frac,
        "queries": n, "cache_entries": len(keys), "table_slots": 1 << tbits,
        "ns_model_only": t[0], "ns_model_plbf": t[1], "ns_cache_only": t[2], "ns_cache_model_plbf": t[3],
        "ns_lightgbm_predict_1thread": t_lgb,
        "overhead_pct": (t[3] - t[1]) / t[1] * 100,
        "cache_hit_rate_in_bench": float(np.isin(H1, np.array(keys, np.uint64)).mean()),
    }
    (out / f"{args.dataset}.json").write_text(json.dumps(res, ensure_ascii=False, indent=1))
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
