"""跑下一批之前的三项核对，输出 results/checks/checks.md。

1. 测试查询池与 LightGBM 训练负样本（以及验证负样本）不相交。
2. 实验 1 中 4MiB 的 "0%" 换成原始误报次数，并给出每个测试 key 只查一次时的静态误报 key 数。
3. 说明 adv* 负载的抽样方式。
"""

import json

import lightgbm as lgb
import numpy as np
import pandas as pd

import common as C


OUT = C.RESULTS / "checks"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    setup = C.Setup()
    sp, ids = setup.split, setup.ids
    lines = ["# 跑下一批之前的三项核对", ""]

    # 1. 不相交
    train_neg, val_neg, test_neg = (set(ids[sp[k]].tolist()) for k in ("neg_train", "neg_val", "neg_test"))
    train_all = set(ids[sp["member_train"] | sp["neg_train"]].tolist())
    n_trees = lgb.Booster(model_file=str(C.CACHE / "cod" / "model48.txt")).num_trees()
    checks1 = {
        "训练负样本": len(train_neg), "验证负样本": len(val_neg), "测试查询池": len(test_neg),
        "测试池 ∩ 训练负样本": len(test_neg & train_neg), "测试池 ∩ 验证负样本": len(test_neg & val_neg),
        "测试池 ∩ 模型全部训练行": len(test_neg & train_all), "验证 ∩ 训练负样本": len(val_neg & train_neg),
        "模型树数": n_trees,
    }
    assert checks1["测试池 ∩ 模型全部训练行"] == 0 and checks1["测试池 ∩ 验证负样本"] == 0
    lines += ["## 1. 查询池与训练集不相交：通过", "",
              "三类负样本按 objID 的哈希值切分（`common.make_split`），"
              "模型只用 `member_train | neg_train` 训练（`common.split_and_score`）。按 objID 求交：", "",
              "| 项 | 数量 |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |" for k, v in checks1.items()]
    lines += ["", "所有查询负载都只从测试查询池里取 key。验证负样本只用来估计 PLBF 各分段的负例比例，不参与查询。", ""]

    # 2. 4MiB 原始计数
    rows = pd.DataFrame(json.loads((C.RESULTS / "exp1_fp_source" / "rows.json").read_text()))
    r4 = rows[rows.budget_kib == 4096]
    lines += ["## 2. 4MiB 下的 0% 是精确的 0", "",
              "实验 1 每格 = 10 个种子 × 1000 万查询 = 1 亿次查询。下表是误报次数合计（直接放行 / 过滤器），"
              "以及单个种子的最大值：", "",
              "| 结构 | 负载 | 直接放行 | 过滤器 | 单种子最大 |", "|---|---|---:|---:|---:|"]
    for (name, wl), g in r4.groupby(["structure", "workload"], sort=False):
        per_seed = g.fp_pass_count + g.fp_filter_count
        lines.append(f"| {name} | {wl} | {g.fp_pass_count.sum():,} | {g.fp_filter_count.sum():,} | "
                     f"{per_seed.max():,} |")

    once = np.arange(setup.q_score.size, dtype=np.int64)
    no_ref = np.zeros(once.size, np.bool_)
    lines += ["", "静态视角：把 99.96 万个测试 key 每个只查一次（AQF 会自适应，但每个 key 只出现一次，"
              "所以基本等于初始误报集合）：", "",
              "| 结构 | 直接放行区内测试 key | backup 误报 key | 每 key 查一次的误报数 |", "|---|---:|---:|---:|"]
    for name, filt in (("PLBF", "bf"), ("PLBF+AQF", "aqf")):
        s = C.Structure(name, filt, True, 4096 * 1024, setup)
        res, _ = s.run(once, 0.0, 0, no_ref)
        info = s.summary()
        lines.append(f"| {name} | {info['test_keys_in_pass']:,} | "
                     f"{info['test_keys_bf_fp'] if filt == 'bf' else int(res[C.FP_FILTER]):,} | "
                     f"{int(res[C.FP_PASS] + res[C.FP_FILTER]):,} |")
    plbf4 = r4[r4.structure == "PLBF"]
    lines += ["",
              f"结论：4MiB 下 PLBF+AQF 在每个负载的 1 亿次查询里误报 {int(r4[r4.structure == 'PLBF+AQF'][['fp_pass_count', 'fp_filter_count']].sum().sum())} 次，"
              f"纯 PLBF 合计 {int(plbf4[['fp_pass_count', 'fp_filter_count']].sum().sum())} 次。"
              "早先版本里纯 PLBF 在对抗负载下的 7.86% 来自 BF 双重哈希的缺陷"
              "（成员极少、每成员 bit 很多的分段里，h1+j·h2 的探测位高度相关），"
              "改为每个探测位独立混合（`common.bf_pos`）后消失，见 `docs/决策记录.md`。", ""]

    # 3. 对抗负载
    lines += ["## 3. adv* 负载的构造：属于重复型（情形 ①），不能叫对抗鲁棒性", "",
              "代码见 `common.simulate`。每条查询以概率 p（2% 或 10%）交给对抗者，其余是测试池上的均匀查询。对抗者：",
              "",
              f"- 手里有已知误报 key 时，以 {C.ADV_REPLAY:.0%} 的概率从中均匀抽一个**重放**，否则从测试池均匀抽一个新 key **探测**；",
              "- 探测得到误报，就把这个 key 加进已知集合；重放时如果不再误报（被 AQF 修掉了），就把它移出；",
              "- 测试池只有 99.96 万个 key，对抗者能找到的误报 key 就是这个池子里的那批（256KiB 下约 1.6–6 千个），之后一直重放。",
              "",
              "所以它是“探测＋重放”：对静态结构，它等价于把查询集中到一小批固定的误报 key 上，属于重复型负载。"
              "论文里应叫“探测重放负载”或“自适应重复负载”，不能拿它说对抗鲁棒性。"
              "实验 2 另加了“全新对抗”负载：按模型分数从高到低取测试池里的 key，每个只查一次。", ""]
    (OUT / "checks.md").write_text("\n".join(lines))
    print("\n".join(lines))


if __name__ == "__main__":
    main()
