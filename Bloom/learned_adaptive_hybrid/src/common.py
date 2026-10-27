"""各实验共用的部分：数据集（COD、Caida）与 48 树模型、PLBF/AQF/负例缓存结构、查询模拟器。"""

import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd
from numba import njit


PROJECT = Path(__file__).resolve().parents[1]
CACHE = PROJECT / "cache"
HTTYF_DATA = PROJECT / "external" / "How-to-Train-Your-Filter" / "data" / "raw"

# 成员训练比例，以及负例的 训练 / 验证 / 测试 切分点（按 key 哈希值的分位数）
DATASETS = {
    "cod": {"raw": PROJECT.parent / "LBF-Gama" / "dataset" / "raw" / "cod",
            "member_train": 2 / 3, "neg_cuts": (0.5333, 2 / 3)},
    # How to Train Your Filter 的 Caida：key 是行号 No.，UDP 为成员，TCP 为非成员
    "caida": {"raw": HTTYF_DATA / "caida.csv", "member_train": 0.5, "neg_cuts": (0.10, 0.20)},
    # How to Train Your Filter 的 Shalla：黑名单域名为成员，Umbrella Top 1M 里不在黑名单的为非成员
    "shalla": {"raw": HTTYF_DATA / "shalla_combined.csv", "member_train": 0.5, "neg_cuts": (0.10, 0.20)},
    # 同一份 Caida，key 改成流（源, 目的, 协议）；TCP 包按时间顺序构成真实查询轨迹（见 load_flow_trace）
    "caida_flow": {"raw": HTTYF_DATA / "caida.csv", "member_train": 0.5, "neg_cuts": (0.10, 0.20)},
}


def url_features(urls):
    """仿照作者 learned/src/filters/utils/url_classifier.py 的 vectorize_url，取其中可直接计数的特征。"""
    u = urls.str
    host = urls.str.split("/", n=1).str[0]
    tld = host.str.rsplit(".", n=1).str[-1]
    feats = {
        "dot": u.count(r"\."), "www": u.count("www"), "at": u.count("@"), "dir": u.count("/"),
        "embed": u.count("//"), "https": u.count("https"), "http": u.count("http"), "pct": u.count("%"),
        "dash": u.count("-"), "eq": u.count("="), "len": u.len(), "host_len": host.str.len(),
        "tld_len": tld.str.len(), "digits": u.count(r"[0-9]"), "letters": u.count(r"[A-Za-z]"),
        "ip": u.contains(r"^\d{1,3}(?:\.\d{1,3}){3}").astype(int),
        "vowels": u.count(r"[aeiouAEIOU]"), "labels": host.str.count(r"\.") + 1,
    }
    return pd.DataFrame(feats)
RESULTS = PROJECT / "results"
FIGURES = PROJECT / "figures"

N_TREES = 48
TREE_BYTES = 700          # 沿用原研究的原生树表示口径
N_SEG = 100               # PLBF 分数分段数，每段单独分配
ALPHA = 0.95              # AQF 成员槽位负载
META_BITS = 3             # AQF 每槽元数据位
RESERVE = 0.05            # AQF 为指纹扩展预留的槽位比例（计入内存）
LEN_BITS = 6              # 负例缓存每条记录的长度字段
ADV_REPLAY = 0.9          # 探测重放对抗者手里有已知误报时，重放它们的概率
ADV_CAP = 200_000

PASS, BF, AQF, EMPTY = 0, 1, 2, 3
SPLIT_SALT, H1_SALT, H2_SALT = 0x5EED, 0xA5A5_0001, 0x3C3C_0002


def splitmix64(x):
    with np.errstate(over="ignore"):
        z = x.astype(np.uint64) + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def load_dataset(name):
    cache = CACHE / name / "data.npz"
    if cache.exists():
        d = np.load(cache, allow_pickle=False)
        return d["ids"], d["y"], d["X"], [str(c) for c in d["features"]]
    raw = DATASETS[name]["raw"]
    if name == "cod":
        frames = [pd.read_csv(raw / f, dtype={"objID": np.int64, "type": "category"})
                  for f in ("train.csv", "test.csv")]
        df = pd.concat(frames, ignore_index=True)
        assert set(df["type"].unique()) == {"galaxy", "star"}, df["type"].unique()
        key, member = "objID", (df["type"] == "galaxy").to_numpy()
        drop = ("objID", "type")
    elif name == "caida_flow":
        pk = pd.read_csv(raw)
        flow = pk["Source"].astype(str) + ">" + pk["Destination"].astype(str) + "#" + pk["Label"].astype(str)
        codes, uniq = pd.factorize(flow, sort=False)
        pk["flow"] = codes
        agg = pk.groupby("flow").agg(label=("Label", "first"), src=("Source", "first"), dst=("Destination", "first"),
                                     len_mean=("Length", "mean"), len_min=("Length", "min"),
                                     len_max=("Length", "max"))
        df = pd.DataFrame({"src": pd.to_numeric(agg.src, errors="coerce").fillna(-1),
                           "dst": pd.to_numeric(agg.dst, errors="coerce").fillna(-1),
                           "len_mean": agg.len_mean, "len_min": agg.len_min, "len_max": agg.len_max})
        df["key"] = pd.util.hash_pandas_object(pd.Series(uniq[agg.index]), index=False).to_numpy()
        df["label"] = agg.label.to_numpy()
        tcp = pk["Label"].to_numpy() == 0
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.save(cache.parent / "trace.npy", codes[tcp].astype(np.int64))   # 按时间顺序的 TCP 包 → 流编号
        key, member = "key", (df["label"] == 1).to_numpy()
        drop = ("key", "label")
    elif name == "shalla":
        raw_df = pd.read_csv(raw, usecols=["url", "label"], dtype={"url": str, "label": np.int8})
        raw_df = raw_df.drop_duplicates("url").reset_index(drop=True)
        df = url_features(raw_df["url"])
        df["key"] = pd.util.hash_pandas_object(raw_df["url"], index=False).to_numpy()
        df["label"] = raw_df["label"].to_numpy()
        key, member = "key", (df["label"] == 1).to_numpy()
        drop = ("key", "label")
    else:
        df = pd.read_csv(raw)
        assert set(df["Label"].unique()) == {0, 1}
        key, member = "No.", (df["Label"] == 1).to_numpy()
        drop = ("No.", "Label")
    assert df[key].is_unique
    features = [c for c in df.columns if c not in drop]
    ids = df[key].to_numpy().astype(np.uint64)
    X = df[features].to_numpy(np.float32)
    assert np.isfinite(X).all()
    cache.parent.mkdir(parents=True, exist_ok=True)
    np.savez(cache, ids=ids, y=member, X=X, features=np.array(features))
    return ids, member, X, features


def make_split(ids, y, name="cod"):
    cfg = DATASETS[name]
    a, b = cfg["neg_cuts"]
    u = (splitmix64(ids ^ np.uint64(SPLIT_SALT)) >> np.uint64(11)).astype(np.float64) / 2.0**53
    neg = ~y
    return {
        "member_train": y & (u < cfg["member_train"]),
        "neg_train": neg & (u < a),
        "neg_val": neg & (u >= a) & (u < b),
        "neg_test": neg & (u >= b),
    }


def split_and_score(ids, y, X, name="cod"):
    cache = CACHE / name / "scores.npz"
    split = make_split(ids, y, name)
    if cache.exists():
        return split, np.load(cache)["score"]
    train = split["member_train"] | split["neg_train"]
    params = {"objective": "binary", "num_leaves": 31, "learning_rate": 0.1,
              "num_threads": 14, "verbose": -1, "seed": 1}
    t0 = time.time()
    booster = lgb.train(params, lgb.Dataset(X[train], label=y[train]), num_boost_round=N_TREES)
    score = booster.predict(X, raw_score=True, num_threads=14)
    print(f"trained {N_TREES} trees in {time.time() - t0:.1f}s")
    booster.save_model(str(CACHE / name / "model48.txt"))
    np.savez(cache, score=score)
    return split, score


def load_flow_trace(setup):
    """caida_flow 的真实查询轨迹：TCP 包按时间顺序，映射成测试查询池里的下标；不在测试池的流的包丢掉。"""
    trace = np.load(CACHE / "caida_flow" / "trace.npy")
    pos = np.full(setup.ids.size, -1, np.int64)
    pos[np.flatnonzero(setup.split["neg_test"])] = np.arange(int(setup.split["neg_test"].sum()))
    q = pos[trace]
    return q[q >= 0]


class Setup:
    """一次性准备好成员、验证负例与测试查询池（测试负例）的分数和哈希。"""

    def __init__(self, name="cod"):
        t0 = time.time()
        self.name = name
        ids, y, X, features = load_dataset(name)
        split, score = split_and_score(ids, y, X, name)
        h1 = splitmix64(ids ^ np.uint64(H1_SALT))
        h2 = splitmix64(ids ^ np.uint64(H2_SALT)) | np.uint64(1)
        test = split["neg_test"]
        self.ids, self.y, self.split = ids, y, split
        self.mem_score, self.h1m, self.h2m = score[y], h1[y], h2[y]
        self.val_score = score[split["neg_val"]]
        self.q_ids, self.q_score, self.h1q, self.h2q = ids[test], score[test], h1[test], h2[test]
        self.q_ra = X[test, features.index("ra")] if "ra" in features else None
        self.cuts = np.unique(np.quantile(np.concatenate([self.mem_score, self.val_score]),
                                          np.linspace(0, 1, N_SEG + 1)[1:-1]))
        # 缓存挡在所有区域前面，所以前缀要避开全部成员，任何成员都不会被误拒
        self.cache_cost = np.zeros(self.h1q.size, np.int64)
        cache_entry_bits(np.sort(self.h1m), self.h1q, np.ones(self.h1q.size, np.bool_),
                         self.cache_cost)
        print(f"{name} setup ready in {time.time() - t0:.1f}s; members={int(y.sum())}, "
              f"neg_val={int(split['neg_val'].sum())}, neg_test={int(test.sum())}")


def bf_fpr(bits_per_key):
    k = np.maximum(1, np.rint(bits_per_key * np.log(2)))
    return (1 - np.exp(-k / bits_per_key)) ** k


def allocate(n, h, budget_bits, filt):
    """每个区域在 PASS 与若干离散滤波器配置中选一个，拉格朗日乘子二分到预算内。"""
    if filt == "bf":
        grid = np.arange(0.25, 40.01, 0.25)
        fpr = bf_fpr(grid)
        cost = n[:, None] * grid[None, :]
    else:
        grid = np.arange(1, 25)
        fpr = 1 - np.exp(-ALPHA * 2.0 ** -grid)
        slots = np.ceil(n / ALPHA) + np.ceil(RESERVE * n)
        cost = slots[:, None] * (grid + META_BITS)[None, :]
    param = grid
    fpr = np.concatenate([[1.0], fpr])
    cost = np.concatenate([np.zeros((n.size, 1)), cost], axis=1)

    def pick(mu):
        idx = np.argmin(h[:, None] * fpr[None, :] + mu * cost, axis=1)
        return idx, cost[np.arange(n.size), idx].sum()

    lo, hi = -40.0, 10.0
    for _ in range(200):
        mid = (lo + hi) / 2
        if pick(10.0 ** mid)[1] <= budget_bits:
            hi = mid
        else:
            lo = mid
    idx, used = pick(10.0 ** hi)
    # 拉格朗日只能落在凸包上，用贪心把剩余预算补给收益/代价比最高的升级
    rows = np.arange(n.size)
    while True:
        d_cost = cost - cost[rows, idx][:, None]
        gain = h[:, None] * (fpr[idx][:, None] - fpr[None, :])
        ok = (d_cost > 0) & (d_cost <= budget_bits - used) & (gain > 0)
        if not ok.any():
            break
        ratio = np.where(ok, gain / np.where(ok, d_cost, 1), -1)
        r, j = np.unravel_index(np.argmax(ratio), ratio.shape)
        used += d_cost[r, j]
        idx[r] = j
    kind = np.where(idx == 0, PASS, BF if filt == "bf" else AQF)
    kind[n == 0] = EMPTY
    chosen = np.where(idx == 0, 0, param[np.maximum(idx - 1, 0)])
    est_fpr = float((h * fpr[idx])[n > 0].sum())
    return kind, chosen, used, est_fpr


@njit(cache=True)
def mix64(z):
    z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
    z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
    return z ^ (z >> np.uint64(31))


@njit(cache=True)
def bf_pos(h, j, m):
    # 每个探测位独立混合；不用 h1 + j*h2 双重哈希，它在 m 很小、k 很大的分段里会明显偏离理想 BF
    return np.int64(mix64(h + np.uint64(j + 1) * np.uint64(0x9E3779B97F4A7C15)) % np.uint64(m))


@njit(cache=True)
def bf_build(h1, h2, reg, off, m, k, bits):
    for i in range(h1.size):
        g = reg[i]
        if m[g] == 0:
            continue
        for j in range(k[g]):
            bits[off[g] + bf_pos(h1[i], j, m[g])] = 1


@njit(cache=True)
def bf_query(h1, h2, reg, off, m, k, bits, out):
    for i in range(h1.size):
        g = reg[i]
        if m[g] == 0:
            out[i] = False
            continue
        hit = True
        for j in range(k[g]):
            if bits[off[g] + bf_pos(h1[i], j, m[g])] == 0:
                hit = False
                break
        out[i] = hit


@njit(cache=True)
def common_prefix_bits(a, b):
    x = a ^ b
    n = 0
    bit = np.uint64(1) << np.uint64(63)
    while n < 64 and (x & bit) == 0:
        n += 1
        bit >>= np.uint64(1)
    return n


@njit(cache=True)
def cache_entry_bits(sorted_mem_h, q_h, eligible, out):
    """负例缓存记录的位数：与全部成员都不冲突的最短 h1 前缀 + 长度字段。"""
    n = sorted_mem_h.size
    for i in range(q_h.size):
        if not eligible[i]:
            out[i] = 0
            continue
        j = np.searchsorted(sorted_mem_h, q_h[i])
        lcp = 0
        if j < n:
            lcp = max(lcp, common_prefix_bits(sorted_mem_h[j], q_h[i]))
        if j > 0:
            lcp = max(lcp, common_prefix_bits(sorted_mem_h[j - 1], q_h[i]))
        out[i] = lcp + 1 + LEN_BITS if lcp < 64 else 0   # 0 表示无法安全缓存


@njit(cache=True)
def ext_match(a, b, nbits):
    if nbits == 0:
        return True
    if nbits >= 64:
        return a == b
    mask = (np.uint64(1) << np.uint64(nbits)) - np.uint64(1)
    return ((a ^ b) & mask) == 0


# simulate 返回数组的下标
FP_PASS, FP_FILTER, FP_TAIL, ADAPTS, ADV_N, Q_H, D_H, C_HITS, C_INS, C_INS_BITS, C_EVICT = range(11)


@njit(cache=True)
def simulate(stream, adv_p, seed, reg_q, kind, bf_fp_q, h1q, h2q,
             space, rbits, off, mem_f, mem_h2, ext, reserve, tail_from,
             cache_cap, cache_cost, ref_h):
    """逐条模拟非成员查询。

    cache_cap>0 时，整个结构前面有一个 FIFO 负例缓存：每次误报（直接放行或 backup）
    都把该 key 记下，之后同一个 key 直接被缓存拒绝。ref_h 标出参考结构（纯 PLBF）的
    直接放行区，用来统计 Q_H（落在该区的查询数）和 D_H（其中不同 key 数）。
    """
    np.random.seed(seed)
    n_pool = reg_q.size
    known = np.empty(ADV_CAP, np.int64)
    cnt = 0
    seen = np.zeros(n_pool, np.uint8)
    in_cache = np.zeros(n_pool, np.uint8)
    fifo = np.empty(n_pool, np.int64)
    head = 0
    tail = 0
    cache_used = 0
    res = np.zeros(11, np.int64)
    for t in range(stream.size):
        adv = adv_p > 0.0 and np.random.random() < adv_p
        replay = False
        slot = 0
        if adv:
            res[ADV_N] += 1
            if cnt > 0 and np.random.random() < ADV_REPLAY:
                slot = np.random.randint(cnt)
                x = known[slot]
                replay = True
            else:
                x = np.random.randint(n_pool)
        else:
            x = stream[t]
        if ref_h[x]:
            res[Q_H] += 1
            if seen[x] == 0:
                seen[x] = 1
                res[D_H] += 1
        g = reg_q[x]
        kd = kind[g]
        fp = False
        if in_cache[x] == 1:
            res[C_HITS] += 1
            kd = EMPTY
        elif kd == PASS:
            fp = True
            res[FP_PASS] += 1
        elif kd == BF:
            fp = bf_fp_q[x]
        elif kd == AQF:
            fx = h1q[x] % space[g]
            lo = off[g]
            hi = off[g + 1]
            j = lo + np.searchsorted(mem_f[lo:hi], fx)
            while j < hi and mem_f[j] == fx:
                if ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g]):
                    fp = True
                    while (ext_match(mem_h2[j], h2q[x], ext[j] * rbits[g])
                           and reserve[g] > 0 and ext[j] * rbits[g] < 64):
                        ext[j] += 1
                        reserve[g] -= 1
                        res[ADAPTS] += 1
                j += 1
        if fp:
            if kd != PASS:
                res[FP_FILTER] += 1
            if t >= tail_from:
                res[FP_TAIL] += 1
            c = cache_cost[x]
            if cache_cap > 0 and c > 0 and c <= cache_cap:
                while cache_used + c > cache_cap:
                    y = fifo[head]
                    head += 1
                    if head == n_pool:
                        head = 0
                    in_cache[y] = 0
                    cache_used -= cache_cost[y]
                    res[C_EVICT] += 1
                fifo[tail] = x
                tail += 1
                if tail == n_pool:      # 环形缓冲：同时在缓存里的 key 数不会超过 n_pool
                    tail = 0
                in_cache[x] = 1
                cache_used += c
                res[C_INS] += 1
                res[C_INS_BITS] += c
        if adv:
            if replay and not fp:
                cnt -= 1
                known[slot] = known[cnt]
            elif not replay and fp and cnt < ADV_CAP:
                known[cnt] = x
                cnt += 1
    return res


class Structure:
    """BF / AQF / PLBF / PLBF+AQF / PLBF+负例缓存。

    cache_frac 是缓存占总预算的比例；free_cache=True 表示缓存无限大且不占预算（理想对照）。
    """

    def __init__(self, name, filt, use_model, budget_bytes, setup, cache_frac=0.0,
                 free_cache=False):
        self.name = name
        self.budget_kib = budget_bytes // 1024
        self.cache_frac = cache_frac
        self.model_bytes = N_TREES * TREE_BYTES if use_model else 0
        self.cache_bits = int(budget_bytes * cache_frac) * 8
        budget_bits = (budget_bytes - self.model_bytes) * 8 - self.cache_bits
        if free_cache:
            self.cache_bits = 1 << 62
        mem_score, h1m, h2m = setup.mem_score, setup.h1m, setup.h2m
        self.cuts = setup.cuts if use_model else np.empty(0)
        reg_m = np.searchsorted(self.cuts, mem_score, side="right").astype(np.int32)
        nreg = self.cuts.size + 1
        n = np.bincount(reg_m, minlength=nreg).astype(np.float64)
        if use_model:
            cnt = np.bincount(np.searchsorted(self.cuts, setup.val_score, side="right"),
                              minlength=nreg)
            h = (cnt + 0.5) / (cnt.sum() + 0.5 * nreg)
        else:
            h = np.ones(1)
        self.kind, self.param, used, self.est_fpr = allocate(n, h, budget_bits, filt)
        self.filter_bytes = used / 8
        self.feasible = not (not use_model and self.kind[0] == PASS)
        self.n = n

        # backup BF
        self.m = np.where(self.kind == BF, np.maximum(1, np.floor(self.param * n)), 0).astype(np.int64)
        self.k = np.where(self.kind == BF,
                          np.maximum(1, np.rint(self.param * np.log(2))), 0).astype(np.int64)
        self.bf_off = np.concatenate([[0], np.cumsum(self.m)]).astype(np.int64)
        self.bits = np.zeros(max(1, self.bf_off[-1]), np.uint8)
        in_bf = self.kind[reg_m] == BF
        bf_build(h1m[in_bf], h2m[in_bf], reg_m[in_bf], self.bf_off, self.m, self.k, self.bits)

        # 自适应指纹过滤器：fingerprint = h1 mod (槽数 * 2^r)，扩展位取自 h2
        self.rbits = np.where(self.kind == AQF, self.param, 0).astype(np.int64)
        base_slots = np.ceil(n / ALPHA).astype(np.uint64)
        self.space = np.where(self.kind == AQF,
                              base_slots * (np.uint64(1) << self.rbits.astype(np.uint64)),
                              np.uint64(1)).astype(np.uint64)
        self.reserve0 = np.where(self.kind == AQF, np.ceil(RESERVE * n), 0).astype(np.int64)
        in_aqf = self.kind[reg_m] == AQF
        f = h1m[in_aqf] % self.space[reg_m[in_aqf]]
        order = np.lexsort((f, reg_m[in_aqf]))
        self.mem_f = f[order]
        self.mem_h2 = h2m[in_aqf][order]
        self.aqf_off = np.concatenate(
            [[0], np.cumsum(np.bincount(reg_m[in_aqf], minlength=nreg))]).astype(np.int64)

        # zero-FN：所有成员都必须被接受
        ok = np.empty(int(in_bf.sum()), np.bool_)
        bf_query(h1m[in_bf], h2m[in_bf], reg_m[in_bf], self.bf_off, self.m, self.k, self.bits, ok)
        assert ok.all(), f"{name}: BF false negative"
        assert (self.kind[reg_m] != EMPTY).all()
        self.bind_queries(setup)

    def bind_queries(self, setup):
        self.reg_q = np.searchsorted(self.cuts, setup.q_score, side="right").astype(np.int32)
        self.h1q, self.h2q = setup.h1q, setup.h2q
        self.bf_fp_q = np.empty(self.h1q.size, np.bool_)
        bf_query(self.h1q, self.h2q, self.reg_q, self.bf_off, self.m, self.k, self.bits, self.bf_fp_q)
        self.bf_fp_q &= self.kind[self.reg_q] == BF
        self.in_pass_q = self.kind[self.reg_q] == PASS
        self.cache_cost = setup.cache_cost

    def run(self, stream, adv_p, seed, ref_h):
        ext = np.zeros(self.mem_f.size, np.int64)
        reserve = self.reserve0.copy()
        res = simulate(stream, adv_p, seed, self.reg_q, self.kind.astype(np.int64),
                       self.bf_fp_q, self.h1q, self.h2q, self.space, self.rbits,
                       self.aqf_off, self.mem_f, self.mem_h2, ext, reserve,
                       int(stream.size * 0.8), self.cache_bits, self.cache_cost, ref_h)
        return res, int(self.reserve0.sum() - reserve.sum())

    def summary(self):
        return {
            "name": self.name, "budget_kib": self.budget_kib, "feasible": bool(self.feasible),
            "cache_frac": self.cache_frac,
            "cache_bytes": -1 if self.cache_bits == 1 << 62 else self.cache_bits // 8,
            "model_bytes": self.model_bytes, "filter_bytes": round(self.filter_bytes),
            "est_val_fpr": self.est_fpr,
            "pass_regions": int((self.kind == PASS).sum()),
            "members_in_filter": int(self.n[(self.kind == BF) | (self.kind == AQF)].sum()),
            "test_keys_in_pass": int(self.in_pass_q.sum()),
            "test_keys_bf_fp": int(self.bf_fp_q.sum()),
        }
