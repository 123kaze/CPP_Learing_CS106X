"""校验：抽象 AQF（common.simulate 里的 AQF 分支）与作者的 AdaptiveQF（external/aqf_port）对同一查询流的结果。

两边都用纯 AQF：同样的成员（h1 哈希值）、同样的 2^q 个槽、同样的 r，查询流取自实验 2 的负载。
抽象版把全部空槽都当作扩展预留槽，和真实 AQF 一致。

用法：python src/validate_aqf.py
"""

import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

import common as C
from exp2_repetition_cache import make_stream


DRIVER = C.PROJECT / "external" / "aqf_port" / "aqf_driver"
OUT = C.RESULTS / "validate_aqf"
R_BITS = (5, 7, 9)
WORKLOADS = {"uniform-全部": ("uniform", None), "zipf1.1-全部": ("zipf", None, 1.1),
             "uniform-10万": ("uniform", 100_000)}


def abstract_run(setup, qbits, rbits, stream):
    n = setup.h1m.size
    space = np.uint64(1) << np.uint64(qbits + rbits)
    mem_f = np.sort(setup.h1m % space)
    order = np.argsort(setup.h1m % space, kind="stable")
    res = C.simulate(stream, 0.0, 0, np.zeros(setup.h1q.size, np.int32), np.array([C.AQF], np.int64),
                     np.zeros(setup.h1q.size, np.bool_), setup.h1q, setup.h2q,
                     np.array([space], np.uint64), np.array([rbits], np.int64),
                     np.array([0, n], np.int64), mem_f, setup.h2m[order],
                     np.zeros(n, np.int64), np.array([(1 << qbits) - n], np.int64),
                     int(stream.size * 0.8), 0, np.zeros(setup.h1q.size, np.int64),
                     np.zeros(setup.h1q.size, np.bool_))
    return {"fp": int(res[C.FP_FILTER]), "fp_tail20": int(res[C.FP_TAIL]),
            "adaptations": int(res[C.ADAPTS]),
            "size_bytes_model": (1 << qbits) * (rbits + C.META_BITS) / 8}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for ds in ("cod", "caida"):
            setup = C.Setup(ds)
            n = setup.h1m.size
            qbits = int(np.ceil(np.log2(n / 0.95)))
            mfile = Path(tmp) / f"{ds}_m.u64"
            setup.h1m.astype("<u8").tofile(mfile)
            for wl, spec in WORKLOADS.items():
                stream = make_stream(spec, setup.h1q.size, np.random.default_rng(2000), np.arange(1))
                qfile = Path(tmp) / "q.u64"
                setup.h1q[stream].astype("<u8").tofile(qfile)
                for r in R_BITS:
                    out = subprocess.run([str(DRIVER), str(qbits), str(r), str(mfile), str(qfile)],
                                         capture_output=True, text=True, check=True).stdout
                    real = json.loads(out.strip().splitlines()[-1])
                    ab = abstract_run(setup, qbits, r, stream)
                    q = stream.size
                    rows.append({"dataset": ds, "members": n, "qbits": qbits, "rbits": r, "workload": wl,
                                 "queries": q, "real_fpr": real["fp"] / q, "abstract_fpr": ab["fp"] / q,
                                 "real_tail_fpr": real["fp_tail20"] / (q - int(q * 0.8)),
                                 "abstract_tail_fpr": ab["fp_tail20"] / (q - int(q * 0.8)),
                                 "real_adapt": real["adaptations"], "abstract_adapt": ab["adaptations"],
                                 "real_bytes": real["size_bytes"], "abstract_bytes": ab["size_bytes_model"],
                                 "real_full": real["full"]})
                    print(rows[-1])
    df = pd.DataFrame(rows)
    (OUT / "rows.json").write_text(df.to_json(orient="records", force_ascii=False, indent=1))
    lines = ["# 抽象 AQF 与作者 AdaptiveQF 的对照", "",
             "两边用同样的成员哈希、2^q 个槽和 r，查询同一条 1000 万长的非成员流。"
             "真实 AQF 来自 How-to-Train-Your-Filter 仓库的 gqf.c（ARM 移植，见 external/aqf_port），"
             "驱动逻辑照搬作者的 aqf_adapter.c。", "",
             "| 数据集 | q | r | 负载 | 真实 FPR | 抽象 FPR | 真实尾段 FPR | 抽象尾段 FPR | 真实扩展次数 | 抽象扩展次数 | 真实字节 | 抽象按 r+3 bit/槽 |",
             "|---|---:|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for r in rows:
        lines.append(f"| {r['dataset']} | {r['qbits']} | {r['rbits']} | {r['workload']} | {r['real_fpr']:.4%} | "
                     f"{r['abstract_fpr']:.4%} | {r['real_tail_fpr']:.4%} | {r['abstract_tail_fpr']:.4%} | "
                     f"{r['real_adapt']:,} | {r['abstract_adapt']:,} | {r['real_bytes']:,} | {r['abstract_bytes']:,.0f} |")
    rel = (df.abstract_fpr / df.real_fpr).describe()
    byt = (df.real_bytes / df.abstract_bytes).describe()
    lines += ["", f"抽象 FPR ÷ 真实 FPR：中位数 {rel['50%']:.3f}，范围 {rel['min']:.3f}–{rel['max']:.3f}。"
                  f"真实字节 ÷ 抽象字节：中位数 {byt['50%']:.3f}，范围 {byt['min']:.3f}–{byt['max']:.3f}。"]
    (OUT / "report.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
