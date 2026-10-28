"""从 results/*/rows.json 画图，输出到 figures/。

用法：python src/plot_figures.py
"""

import json

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import common as C  # noqa: E402


SURFACE, INK, INK2, MUTED, GRID, AXIS = "#fcfcfb", "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7"
SERIES = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"]   # 已用 validate_palette.js 校验
MARKERS = ["o", "s", "D", "^", "v"]

plt.rcParams.update({
    "font.family": ["Hiragino Sans GB", "Arial Unicode MS"], "axes.unicode_minus": False,
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": AXIS, "axes.labelcolor": INK2, "text.color": INK,
    "xtick.color": MUTED, "ytick.color": MUTED, "xtick.labelcolor": INK2, "ytick.labelcolor": INK2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 9,
    "axes.titlesize": 10, "axes.titleweight": "bold", "legend.frameon": False,
})


def pct(v, _=None):
    if v >= 1e-2:
        return f"{v:.0%}"
    return f"{v * 100:.{max(0, int(-np.floor(np.log10(v * 100))))}f}%"


def plain(v, _=None):
    return f"{v:g}"


def load(name):
    return pd.DataFrame(json.loads((C.RESULTS / name / "rows.json").read_text()))


def save(fig, name):
    C.FIGURES.mkdir(parents=True, exist_ok=True)
    fig.savefig(C.FIGURES / name, dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("wrote", C.FIGURES / name)


def fig_exp1_fpr(df):
    wl_names = {"uniform": "均匀", "zipf1.0": "Zipf 1.0", "zipf1.5": "Zipf 1.5", "drift": "天区漂移",
                "adv2%": "探测重放2%", "adv10%": "探测重放10%"}
    structs = ["BF", "AQF", "PLBF", "PLBF+AQF"]
    q_total = 10_000_000 * df.seed.nunique()
    floor = 1 / q_total
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8), sharey=True)
    for ax, kib in zip(axes, (256, 1024, 4096)):
        d = df[df.budget_kib == kib]
        x = np.arange(len(wl_names))
        for i, st in enumerate(structs):
            g = d[d.structure == st].groupby("workload").fpr.mean().reindex(list(wl_names))
            if g.isna().all():
                ax.text(0.02, 0.04 + 0.07 * i, f"{st}：内存放不下", transform=ax.transAxes,
                        color=INK2, fontsize=8)
                continue
            off = (i - 1.5) * 0.12
            y = g.to_numpy()
            zero = y == 0
            ax.scatter(x[~zero] + off, y[~zero], s=36, marker=MARKERS[i], color=SERIES[i],
                       edgecolor=SURFACE, linewidth=1, label=st, zorder=3)
            if zero.any():
                ax.scatter(x[zero] + off, np.full(zero.sum(), floor), s=36, marker=MARKERS[i],
                           facecolor=SURFACE, edgecolor=SERIES[i], linewidth=1.5, zorder=3)
        ax.axhline(floor, color=AXIS, lw=0.8, ls=(0, (3, 3)))
        ax.set_xticks(x, list(wl_names.values()), rotation=30, ha="right")
        ax.set_yscale("log")
        ax.set_ylim(floor / 3, 1.5)
        ax.yaxis.set_major_formatter(pct)
        bpk = kib * 1024 * 8 / 3e6
        ax.set_title(f"{kib}KiB（每成员 {bpk:.1f} bit）", loc="left")
    axes[0].set_ylabel("FPR（对数轴）")
    axes[0].text(len(wl_names) - 0.5, floor * 1.4, "空心 = 1 亿次查询里 0 次误报", ha="right",
                 color=MUTED, fontsize=7.5)
    h, l = axes[2].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.06))
    fig.suptitle("实验 1：同一内存下四种结构的 FPR", x=0.01, ha="left", y=1.12, fontsize=12)
    save(fig, "fig1_exp1_fpr.png")


def fig_exp1_pass_share(df):
    wl_names = {"uniform": "均匀", "zipf1.0": "Zipf 1.0", "zipf1.5": "Zipf 1.5", "drift": "天区漂移",
                "adv2%": "探测重放2%", "adv10%": "探测重放10%"}
    d = df[df.structure == "PLBF+AQF"]
    fig, ax = plt.subplots(figsize=(7.5, 3.4))
    x = np.arange(len(wl_names))
    w = 0.36
    for i, kib in enumerate((256, 1024)):
        g = d[d.budget_kib == kib].groupby("workload").pass_share.mean().reindex(list(wl_names))
        bars = ax.bar(x + (i - 0.5) * (w + 0.02), g.to_numpy(), w, color=SERIES[i],
                      label=f"{kib}KiB", edgecolor=SURFACE, linewidth=1)
        for b, v in zip(bars, g.to_numpy()):
            ax.text(b.get_x() + b.get_width() / 2, v + 0.015, f"{v:.0%}", ha="center",
                    fontsize=7.5, color=INK2)
    ax.set_xticks(x, list(wl_names.values()))
    ax.set_ylim(0, 1.12)
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:.0%}")
    ax.set_ylabel("剩余误报中来自模型直接放行的比例")
    ax.legend(loc="lower right", ncol=2, bbox_to_anchor=(1, 1.0))
    ax.set_title("实验 1：朴素混合（PLBF+AQF）剩余误报的来源；4MiB 下误报为 0，不画", loc="left", pad=22)
    save(fig, "fig2_exp1_pass_share.png")


EXP2_LINES = ["PLBF", "PLBF+缓存1%", "PLBF+缓存10%", "PLBF+AQF", "PLBF+无限免费缓存"]


def fig_exp2_repetition(df):
    agg = (df.groupby(["budget_kib", "workload", "family", "structure"], sort=False)
             .agg(fpr=("fpr", "mean"), rep=("rep", "mean"), q_h=("q_h", "mean")).reset_index())
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.6))
    for ax, kib in zip(axes, (256, 1024)):
        a = agg[(agg.budget_kib == kib) & (agg.q_h > 0)]
        floor = 1e-6
        for i, st in enumerate(EXP2_LINES):
            g = a[a.structure == st].sort_values("rep")
            y = np.maximum(g.fpr.to_numpy(), floor)
            ax.scatter(g.rep, y, s=30, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                       linewidth=1, zorder=3, label=st)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(pct)
        ax.xaxis.set_major_formatter(plain)
        ax.xaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel("D_H / Q_H（越小越重复；以纯 PLBF 的直接放行区为准）")
        n_wl = a.workload.nunique()
        ax.set_title(f"{kib}KiB：{n_wl} 种负载（Q_H=0 的负载不画）", loc="left")
        for wl, label in (("全新对抗", "全新对抗"), ("每key一次", "每 key 一次"),
                          ("探测重放10%", "探测重放10%"), ("向难负例漂移", "向难负例漂移")):
            p = a[(a.workload == wl) & (a.structure == "PLBF")]
            if len(p):
                ax.annotate(label, (p.rep.iloc[0], p.fpr.iloc[0]), xytext=(-6, 8),
                            textcoords="offset points", ha="right", fontsize=7.5, color=INK2)
    axes[0].set_ylabel("FPR（对数轴）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("实验 2：FPR 随直接放行区重复程度的变化（每点 = 一种负载，10 个种子均值；"
                 "FPR 不只由 D_H/Q_H 决定，故不连线）", x=0.01,
                 ha="left", y=1.1, fontsize=12)
    save(fig, "fig3_exp2_fpr_vs_repetition.png")


EXP2_PICKS = {"uniform-10万": "均匀，10 万 key 池", "uniform-全部": "均匀，全部测试负例",
              "向难负例漂移": "向难负例漂移", "每key一次": "每 key 只查一次"}


def fig_cache_fraction(df, budgets, picks, fname, title):
    fracs = [0] + sorted({round(f * 100) for f in df.cache_frac.unique() if f > 0})
    names = {0: "PLBF", **{f: f"PLBF+缓存{f}%" for f in fracs[1:]}}
    fig, axes = plt.subplots(1, len(budgets), figsize=(5.5 * len(budgets), 4), sharey=True)
    for ax, kib in zip(axes, budgets):
        a = df[df.budget_kib == kib].groupby(["workload", "structure"]).fpr.mean()
        for i, (wl, label) in enumerate(picks.items()):
            y = np.array([a.loc[(wl, names[f])] for f in fracs])
            ratio = y / y.min() if y.min() > 0 else np.where(y == 0, 1.0, np.nan)
            ax.plot(range(len(fracs)), ratio, color=SERIES[i], lw=2, marker=MARKERS[i], ms=6,
                    markeredgecolor=SURFACE, label=label)
        ax.set_xticks(range(len(fracs)), [f"{f}%" for f in fracs])
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
        ax.axhline(1, color=AXIS, lw=0.8)
        ax.set_xlabel("负例缓存占总预算的比例")
        ax.set_title(f"{kib}KiB", loc="left")
    axes[0].set_ylabel("FPR ÷ 该负载下最优比例的 FPR（对数轴）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.05))
    fig.suptitle(title, x=0.01, ha="left", y=1.11, fontsize=12)
    save(fig, fname)


def fig_normalized(df, budgets, fname, title, lines=EXP2_LINES):
    """横轴 = PLBF 全部误报的重复度 D_FP/Q_FP，正好等于 无限免费缓存 FPR / PLBF FPR。"""
    agg = df.groupby(["budget_kib", "workload", "structure"]).fpr.mean().unstack("structure")
    fig, axes = plt.subplots(1, len(budgets), figsize=(5.5 * len(budgets), 4.6), sharey=True)
    for ax, kib in zip(axes, budgets):
        a = agg.loc[kib]
        a = a[a["PLBF"] > 0]
        x = a["PLBF+无限免费缓存"] / a["PLBF"]
        lo = max(x.min() / 2, 1e-5)
        ax.set_xscale("log")
        ax.set_yscale("log")
        ax.plot([lo, 1], [lo, 1], color=MUTED, lw=1, ls=(0, (4, 3)), zorder=1,
                label="y = x：每个误报 key 只付第一次（反馈修正的下界）")
        for i, st in enumerate(lines[1:], start=1):
            y = np.maximum(a[st] / a["PLBF"], lo / 2)
            ax.scatter(x, y, s=30, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                       linewidth=1, zorder=3, label=st)
        ax.axhline(1, color=SERIES[0], lw=1.2, zorder=1, label="PLBF（基准 = 1）")
        for wl, label in (("全新对抗", "每 key 一次 / 全新对抗"), ("探测重放10%", "探测重放10%"),
                          ("向难负例漂移", "向难负例漂移"), ("uniform-全部", "均匀，全部测试负例")):
            if wl in x.index and not (wl == "uniform-全部" and x[wl] > 0.3):   # 太靠近 x=1 会和上一个标注重叠
                ax.annotate(label, (x[wl], a.loc[wl, "PLBF+缓存10%"] / a.loc[wl, "PLBF"]),
                            xytext=(-8, -14 if wl == "全新对抗" else 6), textcoords="offset points",
                            ha="right", fontsize=7.5, color=INK2)
        for axis in (ax.xaxis, ax.yaxis):
            axis.set_major_formatter(plain)
            axis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xlabel("D_FP / Q_FP：纯 PLBF 的误报里不同 key 的占比（越小越重复）")
        ax.set_title(f"{kib}KiB：{len(a)} 种负载", loc="left")
    axes[0].set_ylabel("FPR ÷ 纯 PLBF 的 FPR（对数轴）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=3, bbox_to_anchor=(0.5, 1.08))
    fig.suptitle(title, x=0.01, ha="left", y=1.15, fontsize=12)
    save(fig, fname)


def fig_exp4_policies(df):
    picks = {"向难负例漂移": "向难负例漂移", "uniform-100万": "均匀，100 万 key 池",
             "zipf0.8-全部": "Zipf 0.8，全部测试负例", "zipf1.1-10万": "Zipf 1.1，10 万 key 池"}
    policies = ["FIFO", "LRU", "oracle-LFU", "OPT"]
    budgets = sorted(df.budget_kib.unique())
    a = df.groupby(["budget_kib", "workload", "policy", "cache_frac"]).fpr.mean()
    bound = df[df.cache_frac == 0].groupby(["budget_kib", "workload"]).bound_fpr.mean()
    fig, axes = plt.subplots(len(budgets), len(picks), figsize=(3.3 * len(picks), 3.1 * len(budgets)),
                             sharex=True)
    for r, kib in enumerate(budgets):
        for c, (wl, label) in enumerate(picks.items()):
            ax = axes[r, c]
            for i, pol in enumerate(policies):
                curve = a.loc[(kib, wl, pol)]
                ax.plot(curve.index * 100, curve.to_numpy(), color=SERIES[i], lw=2, marker=MARKERS[i],
                        ms=5, markeredgecolor=SURFACE, label=pol)
            ax.axhline(bound.loc[(kib, wl)], color=MUTED, lw=1, ls=(0, (4, 3)), label="下界（无限免费缓存）")
            ax.set_yscale("log")
            ax.yaxis.set_major_formatter(pct)
            ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
            ax.set_title(f"{kib}KiB · {label}", loc="left", fontsize=9)
            if r == len(budgets) - 1:
                ax.set_xlabel("缓存占预算 %")
        axes[r, 0].set_ylabel("FPR（对数轴）")
    h, l = axes[0, 0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=5, bbox_to_anchor=(0.5, 1.03))
    fig.suptitle("实验 4（Caida）：换淘汰策略能把离下界的差距缩小多少", x=0.01, ha="left", y=1.07,
                 fontsize=12)
    fig.tight_layout()
    save(fig, "fig8_exp4_cache_policy.png")


def fig_exp6_split(summary):
    variants = ["PLBF+缓存", "PLBF+缓存(二次准入)", "PLBF+缓存(64位)", "PLBF+AQF+放行区缓存"]
    budgets = sorted(summary.budget_kib.unique())
    fig, axes = plt.subplots(1, len(budgets), figsize=(7 * len(budgets), 4.8), sharey=True)
    for ax, kib in zip(axes, budgets):
        d = summary[(summary.budget_kib == kib) & (summary.bound > 0)]
        order = d[d.variant == variants[0]].sort_values("gap").workload.tolist()
        x = np.arange(len(order))
        for i, v in enumerate(variants):
            g = d[d.variant == v].set_index("workload").reindex(order)
            ax.scatter(x + (i - 1.5) * 0.15, g.gap, s=30, marker=MARKERS[i], color=SERIES[i],
                       edgecolor=SURFACE, linewidth=1, label=v, zorder=3)
        ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.axhline(2, color=GRID, lw=1)
        ax.set_yscale("log")
        ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xticks(x, order, rotation=60, ha="right", fontsize=7.5)
        ax.set_title(f"{kib}KiB（负载按 PLBF+缓存 离下界的倍数排序）", loc="left")
    axes[0].set_ylabel("各自最优比例下的 FPR ÷ 下界（对数轴）")
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc="upper center", ncol=4, bbox_to_anchor=(0.5, 1.04))
    fig.suptitle("实验 6（Caida）：分工型混合与缓存写入方式，各自离下界多远（虚线 = 下界）", x=0.01,
                 ha="left", y=1.1, fontsize=12)
    save(fig, "fig9_exp6_split_hybrid.png")


def fig_exp7_rule(summary):
    picks = ["规则(上限40%)", "规则(上限30%)", "稳健-相对", "稳健-绝对"]
    keys = summary[["dataset", "budget_kib"]].drop_duplicates().values.tolist()
    labels = [f"{d}\n{k}KiB" for d, k in keys]
    rule40 = summary[summary.pick == "规则(上限40%)"].set_index(["dataset", "budget_kib"])
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(keys))
    for i, pk in enumerate(picks):
        g = summary[summary.pick == pk].set_index(["dataset", "budget_kib"])
        y = [g.loc[tuple(k), "worst_rel"] for k in keys]
        ax.scatter(x + (i - 1.5) * 0.12, y, s=38, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                   linewidth=1, label=pk, zorder=3)
    for j, k in enumerate(keys):
        f = rule40.loc[tuple(k), "frac"]
        capped = f >= 0.399
        ax.text(j, 0.84, f"规则\n{f * 100:.2g}%" + ("\n取上限" if capped else ""), ha="center", va="bottom",
                fontsize=7, color=INK2, transform=ax.get_xaxis_transform())
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(x, labels)
    ax.set_ylabel("最坏相对代价（对数轴）")
    ax.legend(loc="upper left", ncol=4, bbox_to_anchor=(0, 1.13))
    ax.set_title("实验 7：部署前可算的缓存大小规则 vs 事后挑的稳健比例（越低越好）", loc="left", pad=30)
    save(fig, "fig10_exp7_cache_size_rule.png")


def fig_exp8(sb, s8):
    s8 = s8[s8.pick == "规则+HLL(前10%)"].assign(pick="规则+HLL(只看前 10% 查询)")
    d = pd.concat([sb, s8[["dataset", "budget_kib", "pick", "worst_rel"]]])
    picks = ["模型(N_eff=HLL全程)", "模型(全集N)", "实验7规则(上限40%)", "规则+HLL(只看前 10% 查询)"]
    keys = d[["dataset", "budget_kib"]].drop_duplicates().values.tolist()
    fig, ax = plt.subplots(figsize=(10, 4.2))
    x = np.arange(len(keys))
    for i, pk in enumerate(picks):
        g = d[d.pick == pk].set_index(["dataset", "budget_kib"])
        y = [g.loc[tuple(k), "worst_rel"] for k in keys]
        ax.scatter(x + (i - 1.5) * 0.12, y, s=38, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                   linewidth=1, label=pk, zorder=3)
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(x, [f"{a}\n{b}KiB" for a, b in keys])
    ax.set_ylabel("最坏相对代价（对数轴）")
    ax.legend(loc="upper left", ncol=2, bbox_to_anchor=(0, 1.2))
    ax.set_title("实验 8：不拟合常数的模型，N 用全集 vs 用 HLL 估出的 N_eff（越低越好）", loc="left", pad=42)
    save(fig, "fig11_exp8_model_neff.png")


def fig_exp9(t):
    picks = ["误报流模型(W,s 由 Q_F,D_F,头部占比拟合)", "在线控制器(只增不减)", "固定40%"]
    labels = {"误报流模型(W,s 由 Q_F,D_F,头部占比拟合)": "误报流模型（测量带后见之明）",
              "在线控制器(只增不减)": "在线控制器（只增不减）", "固定40%": "固定 40%"}
    w = t[t.pick.isin(picks)].groupby(["dataset", "budget_kib", "pick"]).rel.max().reset_index()
    keys = w[["dataset", "budget_kib"]].drop_duplicates().values.tolist()
    fig, ax = plt.subplots(figsize=(11, 4.2))
    x = np.arange(len(keys))
    for i, pk in enumerate(picks):
        g = w[w.pick == pk].set_index(["dataset", "budget_kib"])
        y = [g.loc[tuple(k), "rel"] if tuple(k) in g.index else np.nan for k in keys]
        ax.scatter(x + (i - 1) * 0.15, y, s=38, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                   linewidth=1, label=labels[pk], zorder=3)
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
    real = [j for j, k in enumerate(keys) if k[0].endswith("_flow")]
    ax.axvspan(min(real) - 0.5, max(real) + 0.5, color=GRID, alpha=0.5, zorder=0)
    ax.text((min(real) + max(real)) / 2, 0.97, "真实轨迹", ha="center", va="top", fontsize=8, color=INK2,
            transform=ax.get_xaxis_transform())
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(x, [f"{a}\n{b}KiB" for a, b in keys], fontsize=8)
    ax.set_ylabel("最坏相对代价（对数轴）")
    ax.legend(loc="upper left", ncol=3, bbox_to_anchor=(0, 1.13))
    ax.set_title("实验 9：误报流模型与只增不减控制器，各设置下的最坏代价（越低越好）", loc="left", pad=30)
    save(fig, "fig12_exp9_fp_stream.png")


def fig_exp10(a, picks=("误报流模型", "在线控制器", "learned stacked(事后最优)", "SkiQF式二次准入", "PLBF(0%缓存)"),
              fname="fig13_exp10_baselines.png", title="实验 10：与基线对比（5 个种子；越低越好）"):
    picks = list(picks)
    w = a[a.method.isin(picks)].groupby(["dataset", "budget_kib", "method"]).rel.max().reset_index()
    keys = w[["dataset", "budget_kib"]].drop_duplicates().values.tolist()
    fig, ax = plt.subplots(figsize=(max(12, 1.0 * len(keys)), 4.4))
    x = np.arange(len(keys))
    for i, pk in enumerate(picks):
        g = w[w.method == pk].set_index(["dataset", "budget_kib"])
        y = [min(g.loc[tuple(k), "rel"], 2000) if tuple(k) in g.index else np.nan for k in keys]
        ax.scatter(x + (i - 2) * 0.13, y, s=36, marker=MARKERS[i], color=SERIES[i], edgecolor=SURFACE,
                   linewidth=1, label=pk, zorder=3)
    ax.axhline(1, color=MUTED, lw=1, ls=(0, (4, 3)))
    real = [j for j, k in enumerate(keys) if k[0].endswith("_flow")]
    if real:
        ax.axvspan(min(real) - 0.5, max(real) + 0.5, color=GRID, alpha=0.5, zorder=0)
        ax.text((min(real) + max(real)) / 2, 1.01, "真实轨迹", ha="center", va="bottom", fontsize=8, color=INK2,
                transform=ax.get_xaxis_transform())
    ax.set_yscale("log")
    ax.yaxis.set_major_formatter(lambda v, _: f"{v:g}×")
    ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
    ax.set_xticks(x, [f"{d}\n{b}KiB" for d, b in keys], fontsize=8)
    ax.set_ylabel("所有负载上的最坏相对代价（对数轴）")
    ax.legend(loc="upper left", ncol=5, bbox_to_anchor=(0, 1.17), fontsize=8)
    ax.set_title(title, loc="left", pad=40)
    save(fig, fname)


def main():
    exp1 = load("exp1_fp_source")
    fig_exp1_fpr(exp1)
    fig_exp1_pass_share(exp1)
    exp2 = load("exp2_repetition_cache")
    fig_exp2_repetition(exp2)
    fig_cache_fraction(exp2, (256, 1024), EXP2_PICKS, "fig4_exp2_cache_fraction.png",
                       "实验 2：缓存比例选错的代价随负载变化")
    fig_normalized(exp2, (256, 1024), "fig5_exp2_normalized.png",
                   "实验 2：按全部误报的重复度看，负例缓存贴着下界，朴素混合远离下界")
    exp3_path = C.RESULTS / "exp3_caida_working_set" / "rows.json"
    if exp3_path.exists():
        exp3 = load("exp3_caida_working_set")
        fig_cache_fraction(exp3, (128, 256, 1024),
                           {"zipf1.1-10万": "Zipf 1.1，10 万 key 池", "zipf1.1-全部": "Zipf 1.1，全部测试负例",
                            "uniform-全部": "均匀，全部测试负例", "探测重放10%": "探测重放 10%"},
                           "fig6_exp3_caida_cache_fraction.png",
                           "实验 3（Caida）：误报工作集远大于缓存时，缓存比例选错的代价")
        fig_normalized(exp3, (128, 256, 1024), "fig7_exp3_caida_normalized.png",
                       "实验 3（Caida）：按全部误报的重复度看各结构离下界多远",
                       lines=["PLBF", "PLBF+缓存1%", "PLBF+缓存10%", "PLBF+AQF", "PLBF+无限免费缓存"])
    if (C.RESULTS / "exp4_cache_policy" / "rows.json").exists():
        fig_exp4_policies(load("exp4_cache_policy"))
    if (C.RESULTS / "exp6_split_hybrid" / "summary.json").exists():
        fig_exp6_split(pd.read_json(C.RESULTS / "exp6_split_hybrid" / "summary.json"))
    if (C.RESULTS / "exp7_cache_size_rule" / "summary.json").exists():
        fig_exp7_rule(pd.read_json(C.RESULTS / "exp7_cache_size_rule" / "summary.json"))
    if (C.RESULTS / "exp8_cap_and_neff" / "summary_b.json").exists():
        fig_exp8(pd.read_json(C.RESULTS / "exp8_cap_and_neff" / "summary_b.json"),
                 pd.read_json(C.RESULTS / "exp8_cap_and_neff" / "summary.json"))
    if (C.RESULTS / "exp9_fp_stream_controller" / "summary.json").exists():
        fig_exp9(pd.read_json(C.RESULTS / "exp9_fp_stream_controller" / "summary.json"))
    if (C.RESULTS / "exp10_baselines" / "summary.json").exists():
        fig_exp10(pd.read_json(C.RESULTS / "exp10_baselines" / "summary.json"))
    if (C.RESULTS / "exp11_original_baselines" / "summary.json").exists():
        fig_exp10(pd.read_json(C.RESULTS / "exp11_original_baselines" / "summary.json"),
                  picks=("误报流模型", "在线控制器", "Gama-PLBF", "learned stacked(事后最优)", "Stacked(原版)"),
                  fname="fig14_exp11_original_baselines.png",
                  title="实验 11：加入原版 Gama 与原版 Stacked 后的对比（5 个种子；>2000× 截断；越低越好）")
    if (C.RESULTS / "exp12_gama_cache" / "summary.json").exists():
        fig_exp10(pd.read_json(C.RESULTS / "exp12_gama_cache" / "summary.json"),
                  picks=("Gama＋缓存", "Gama-PLBF", "误报流模型", "learned stacked(事后最优)", "Stacked(原版)"),
                  fname="fig15_exp12_gama_cache.png",
                  title="实验 12：Gama＋缓存（Gama 是 r=0 的特例），含每成员 ≥8 bit 的高预算点（>2000× 截断；越低越好）")


if __name__ == "__main__":
    main()
