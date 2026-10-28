"""实验 11：补两个原版基线，并入实验 10 的对比。

1. Stacked Filter 原版（Deeds 等人，How-to-Train-Your-Filter 仓库自带的 C++ 实现，Bloom 层，多层成本优化）。
   驱动见 external/stacked_port（原版代码不改，只给头文件做了 macOS/clang 兼容的副本）。
   输入同 HTTYF：正例 = 全部成员；负例 = 前 25% 查询里的不同负 key，按次数降序，附累计频率；总位数 = 预算。
   它不用模型（原版就是非 learned 的）。
2. Gama 原版的模型大小搜索（Loop-based 精确版）：同样参数训练 200 轮 LightGBM，候选树数取前缀，
   剩余预算交给 PLBF 分配，按验证集估计 FPR 选树数；不加缓存。

评估口径与实验 10 相同：前 25% 是学习期，只比后 75%；合成负载 5 个种子，真实轨迹 1 次。

用法：python src/exp11_original_baselines.py --dataset caida [--seeds 5]
      python src/exp11_original_baselines.py --report
"""

import argparse
import copy
import json
import subprocess
import tempfile
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import make_stream, workloads
from exp9_fp_stream_controller import SETTINGS


OUT = C.RESULTS / "exp11_original_baselines"
STACKED = C.PROJECT / "external" / "stacked_port" / "stacked_driver"
GAMA_MAX = 200
GAMA_TREES = (1, 2, 4, 8, 12, 16, 24, 32, 48, 64, 96, 128, 160, 200)


def gama_scores(setup, ds):
    """200 轮模型，返回 {树数: 全部 key 的分数}（缓存到 cache/<ds>/gama_scores.npz）。"""
    cache = C.CACHE / ds / "gama_scores.npz"
    if cache.exists():
        d = np.load(cache)
        return {int(k[1:]): d[k] for k in d.files}
    ids, y, X, _ = C.load_dataset(ds)
    train = setup.split["member_train"] | setup.split["neg_train"]
    params = {"objective": "binary", "num_leaves": 31, "learning_rate": 0.1,
              "num_threads": 14, "verbose": -1, "seed": 1}
    booster = lgb.train(params, lgb.Dataset(X[train], label=y[train]), num_boost_round=GAMA_MAX)
    booster.save_model(str(C.CACHE / ds / "model200.txt"))
    out = {t: booster.predict(X, raw_score=True, num_iteration=t, num_threads=14) for t in GAMA_TREES}
    np.savez(cache, **{f"t{t}": v for t, v in out.items()})
    return out


def gama_setup(setup, score):
    s = copy.copy(setup)
    y, sp = setup.y, setup.split
    s.mem_score, s.val_score, s.q_score = score[y], score[sp["neg_val"]], score[sp["neg_test"]]
    s.cuts = np.unique(np.quantile(np.concatenate([s.mem_score, s.val_score]),
                                   np.linspace(0, 1, C.N_SEG + 1)[1:-1]))
    return s


def run(ds, seeds, budgets=None, suffix=""):
    budgets = budgets or SETTINGS[ds]
    t0 = time.time()
    setup = C.Setup(ds)
    n_pool = setup.q_score.size
    order = np.argsort(setup.q_score, kind="stable")
    scores = gama_scores(setup, ds)
    diff48 = float(np.abs(scores[48][setup.y] - setup.mem_score).max())
    print(f"{ds}: 200 轮模型的 48 树前缀与现有 48 树模型的最大分数差 {diff48:.2e}", flush=True)

    # Gama：每个预算按验证集估计 FPR 选树数
    gama = {}
    for kib in budgets:
        best = None
        for t in GAMA_TREES:
            if t * C.TREE_BYTES >= kib * 1024:
                continue
            gs = gama_setup(setup, scores[t])
            st = C.Structure(f"Gama-{t}", "bf", True, kib * 1024, gs, n_trees=t)
            if best is None or st.est_fpr < best[0]:
                best = (st.est_fpr, t, st)
        st = best[2]
        st.fp_static = st.in_pass_q | st.bf_fp_q
        gama[kib] = (best[1], st)
        print(f"{ds} {kib}KiB: Gama 选 {best[1]} 棵树，验证集估计 FPR {best[0]:.4%}", flush=True)

    if ds.endswith("_flow"):
        wls, seeds = [("真实轨迹", None)], 1
    else:
        pools = {"1万": 10_000, "10万": 100_000, **({"100万": 1_000_000} if n_pool > 1_500_000 else {}),
                 "全部": None}
        wls = [(w[0], w[3]) for w in workloads(pools) if w[1] != "probe-replay"]
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        setup.h1m.astype("<u8").tofile(tmp / "pos.u64")
        setup.h1q.astype("<u8").tofile(tmp / "qry.u64")
        for name, spec in wls:
            for seed in range(seeds):
                stream = (C.load_flow_trace(setup) if spec is None
                          else make_stream(spec, n_pool, np.random.default_rng(2000 + seed), order))
                tail = stream.size // 4
                # 原版 stacked 的训练负例：前 25% 里的不同负 key，按次数降序
                cnt = np.bincount(stream[:tail], minlength=n_pool)
                negs = np.flatnonzero(cnt)
                negs = negs[np.argsort(-cnt[negs], kind="stable")]
                setup.h1q[negs].astype("<u8").tofile(tmp / "neg.u64")
                (np.cumsum(cnt[negs]) / cnt[negs].sum()).astype("<f8").tofile(tmp / "cdf.f64")
                for kib in budgets:
                    res = subprocess.run([str(STACKED), str(kib * 1024 * 8), str(tmp / "pos.u64"), str(tmp / "neg.u64"),
                                          str(tmp / "cdf.f64"), str(tmp / "qry.u64"), str(tmp / "out.u8")],
                                         capture_output=True, text=True, check=True)
                    info = json.loads(res.stdout.strip().splitlines()[-1])
                    assert info["false_negatives"] == 0
                    acc = np.fromfile(tmp / "out.u8", np.uint8).astype(bool)
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                 "method": "Stacked(原版)", "frac": info["actual_bits"] / (kib * 1024 * 8),
                                 "fpr": float(acc[stream[tail:]].mean())})
                    t, st = gama[kib]
                    rows.append({"dataset": ds, "budget_kib": kib, "workload": name, "seed": seed,
                                 "method": f"Gama-PLBF", "frac": t, "fpr": float(st.fp_static[stream[tail:]].mean())})
            print(f"{ds} {name} done at {time.time() - t0:.1f}s", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_json(OUT / f"rows_{ds}{suffix}.json", orient="records", force_ascii=False, indent=1)
    json.dump({str(k): v[0] for k, v in gama.items()}, open(OUT / f"gama_trees_{ds}{suffix}.json", "w"))


ORDER = ["误报流模型", "在线控制器", "Gama-PLBF", "PLBF(0%缓存)", "Stacked(原版)", "learned stacked(事后最优)",
         "SkiQF式二次准入", "TODS-CAF(PLBF)", "纯AQF"]


def report():
    e10 = pd.concat([pd.read_json(p) for p in sorted((C.RESULTS / "exp10_baselines").glob("rows_*.json"))])
    e11 = pd.concat([pd.read_json(p) for p in sorted(OUT.glob("rows_*.json"))])
    df = pd.concat([e10, e11])
    a = df.groupby(["dataset", "budget_kib", "workload", "method"]).fpr.mean().reset_index()
    best = a.groupby(["dataset", "budget_kib", "workload"]).fpr.transform("min")
    eps = a.workload.map(lambda w: 1 / (0.75 * (5_775_801 if w == "真实轨迹" else 10_000_000)))
    a["rel"] = (a.fpr + eps) / (best + eps)
    a.to_json(OUT / "summary.json", orient="records", force_ascii=False, indent=1)
    trees = {}
    for p in OUT.glob("gama_trees_*.json"):
        ds = p.stem.split("_", 2)[2].removesuffix("_hi")
        trees.setdefault(ds, {}).update(json.load(open(p)))
    lines = ["# 实验 11：补原版 Stacked 与 Gama 后的完整对比", "",
             "口径同实验 10：前 25% 学习期，只比后 75%；相对“网格比例与所有方法里该负载最好的那个”，各加 1 次误报平滑。"
             "每格：最坏相对代价 / 中位数。", "",
             "| 数据集 | 预算 | Gama 选的树数 | " + " | ".join(ORDER) + " |", "|---|---:|---:|" + "---|" * len(ORDER)]
    for (ds, kib), g in a.groupby(["dataset", "budget_kib"], sort=False):
        cells = []
        for m in ORDER:
            h = g[g.method == m]
            cells.append("—" if h.empty else f"{h.rel.max():.2f}× / {h.rel.median():.2f}×")
        lines.append(f"| {ds} | {kib}KiB | {trees.get(ds, {}).get(str(kib), '—')} | " + " | ".join(cells) + " |")
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
