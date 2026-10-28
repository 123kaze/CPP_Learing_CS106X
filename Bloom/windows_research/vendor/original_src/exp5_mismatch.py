"""实验 5（预览）：离线按一条轨迹选缓存比例，拿到另一条轨迹上用，代价多大。

不跑新模拟，直接用实验 4 的结果：对每个预算、每种淘汰策略、每对负载 (W1, W2)，
代价 = FPR(在 W1 上最优的比例, W2) ÷ W2 上最优比例的 FPR。
错配分四类：同池换分布（例：Zipf 1.1 → Zipf 0.8）、同分布换查询池大小、平稳 → 漂移、漂移 → 平稳。
局限：W1 用的是整条轨迹而不是轨迹前缀，等于假设训练轨迹和部署时的“平稳部分”完全一样。

用法：python src/exp5_mismatch.py
"""

import json
from itertools import permutations

import pandas as pd

import common as C


SRC = C.RESULTS / "exp4_cache_policy"
OUT = C.RESULTS / "exp5_mismatch"
SPECIAL = {"每key一次", "全新对抗", "向难负例漂移"}


def classify(w1, w2):
    if w1 in SPECIAL or w2 in SPECIAL:
        if w2 == "向难负例漂移" and w1 not in SPECIAL:
            return "平稳 → 漂移"
        if w1 == "向难负例漂移" and w2 not in SPECIAL:
            return "漂移 → 平稳"
        return "其他（含每 key 一次 / 全新对抗）"
    d1, p1 = w1.split("-")
    d2, p2 = w2.split("-")
    if p1 == p2:
        return "同池换分布"
    if d1 == d2:
        return "同分布换查询池大小"
    return "分布和查询池都不同"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(json.loads((SRC / "rows.json").read_text()))
    a = df.groupby(["budget_kib", "policy", "workload", "cache_frac"]).fpr.mean()
    rows = []
    for (kib, pol), g in a.groupby(level=["budget_kib", "policy"]):
        piv = g.droplevel([0, 1]).unstack("cache_frac")
        best_f = piv.idxmin(axis=1)
        best = piv.min(axis=1)
        for w1, w2 in permutations(piv.index, 2):
            f = best_f[w1]
            regret = piv.loc[w2, f] / best[w2] if best[w2] > 0 else (1.0 if piv.loc[w2, f] == 0 else float("inf"))
            rows.append({"budget_kib": kib, "policy": pol, "train": w1, "test": w2, "train_frac": f,
                         "test_best_frac": best_f[w2], "regret": regret, "class": classify(w1, w2)})
    r = pd.DataFrame(rows)
    (OUT / "rows.json").write_text(r.to_json(orient="records", force_ascii=False, indent=1))

    lines = ["# 实验 5（预览）：离线选比例在负载错配下的代价", "",
             "数据来自实验 4（Caida）。代价 = 用训练负载上最优的缓存比例去跑测试负载的 FPR ÷ 测试负载自己的最优 FPR。",
             "训练负载用的是整条轨迹，不是轨迹前缀，所以这里的代价是乐观估计。", "",
             "| 预算 | 策略 | 错配类型 | 对数 | 中位数 | 90 分位 | 最差 | 最差的一对（训练 → 测试） |",
             "|---:|---|---|---:|---:|---:|---:|---|"]
    order = ["同池换分布", "同分布换查询池大小", "分布和查询池都不同", "平稳 → 漂移", "漂移 → 平稳",
             "其他（含每 key 一次 / 全新对抗）"]
    for (kib, pol), g in r.groupby(["budget_kib", "policy"]):
        for cls in order:
            h = g[g["class"] == cls]
            if h.empty:
                continue
            w = h.loc[h.regret.idxmax()]
            lines.append(f"| {kib}KiB | {pol} | {cls} | {len(h)} | {h.regret.median():.2f}× | "
                         f"{h.regret.quantile(0.9):.2f}× | {h.regret.max():.2f}× | "
                         f"{w.train}（{w.train_frac:.0%}）→ {w.test}（最优 {w.test_best_frac:.0%}） |")
    (OUT / "report.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
