import argparse
import copy

import pandas as pd

from compare_lighttree_lbf_plbf import (
    evaluate_single_threshold,
    train_single_threshold_lbf,
)
from tune_student_url_plbf import evaluate_query, load_data, train_plbf


def tree_configs(args):
    for rounds in args.tree_rounds:
        for leaves in args.tree_leaves:
            for depth in args.tree_depths:
                for c_value in args.c_values:
                    yield {
                        "tree_rounds": rounds,
                        "tree_leaves": leaves,
                        "tree_depth": depth,
                        "tree_learning_rate": args.tree_learning_rate,
                        "tree_min_child_samples": args.tree_min_child_samples,
                        "c_value": c_value,
                    }


def data_with_config(data, config, seed):
    current = copy.copy(data)
    current.update(
        {
            "tree_rounds": config["tree_rounds"],
            "tree_leaves": config["tree_leaves"],
            "tree_depth": config["tree_depth"],
            "tree_learning_rate": config["tree_learning_rate"],
            "tree_min_child_samples": config["tree_min_child_samples"],
            "seed": seed,
        }
    )
    return current


def train_query_aware_single_lbf(data, memory_kib, args):
    best = None
    for config in tree_configs(args):
        current = data_with_config(data, config, args.seed)
        local_args = copy.copy(args)
        local_args.c_value = config["c_value"]
        result = train_single_threshold_lbf(current, memory_kib, local_args)
        if result is None:
            continue
            metrics = evaluate_single_threshold(result, current)
        row = {
            "method": "query_aware_single_lbf",
            "memory_kib": memory_kib,
            "fpr": metrics["fpr"],
            "fnr": metrics["fnr"],
            "construction_seconds": result["construction_seconds"],
            "estimated_fpr": result["estimated_fpr"],
            "model_bits": result["model_bits"],
            "threshold": result["threshold"],
            "config": config,
        }
        if best is None or row["estimated_fpr"] < best["estimated_fpr"]:
            best = row
    return best


def train_query_aware_plbf(data, memory_kib, args):
    best = None
    for config in tree_configs(args):
        for bucket_count in args.bucket_counts:
            current = data_with_config(data, config, args.seed)
            result = train_plbf(
                current,
                memory_kib,
                "lighttree",
                config["c_value"],
                bucket_count,
                args.step_bits,
                "dp",
                "combined_quantile",
                32,
            )
            if result is None:
                continue
            metrics = evaluate_query(result, current)
            row = {
                "method": "query_aware_lighttree_plbf",
                "memory_kib": memory_kib,
                "fpr": metrics["fpr"],
                "fnr": metrics["fnr"],
                "construction_seconds": result["construction_seconds"],
                "estimated_fpr": result["estimated_fpr"],
                "model_bits": result["model_bits"],
                "bucket_count": bucket_count,
                "config": config,
            }
            if best is None or row["estimated_fpr"] < best["estimated_fpr"]:
                best = row
    return best


def config_text(row):
    config = row["config"]
    parts = [
        f"rounds={config['tree_rounds']}",
        f"leaves={config['tree_leaves']}",
        f"depth={config['tree_depth']}",
        f"C={config['c_value']:g}",
        f"model_bits={row['model_bits']}",
    ]
    if "bucket_count" in row:
        parts.append(f"buckets={row['bucket_count']}")
    if "threshold" in row:
        parts.append(f"threshold={row['threshold']:.8g}")
    return ",".join(parts)


def print_row(row):
    print(
        f"memory_kib={row['memory_kib']} "
        f"method={row['method']} "
        f"fpr={row['fpr']:.12g} "
        f"fnr={row['fnr']:.12g} "
        f"estimated_fpr={row['estimated_fpr']:.12g} "
        f"time={row['construction_seconds']:.6f}s "
        f"{config_text(row)}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--query-validation-fraction", type=float, default=0.5)
    parser.add_argument("--c-values", type=float, nargs="+", default=[0.1, 1.0, 10.0])
    parser.add_argument("--bucket-counts", type=int, nargs="+", default=[16, 32, 64])
    parser.add_argument("--step-bits", type=int, default=1024)
    parser.add_argument("--max-thresholds", type=int, default=512)
    parser.add_argument("--tree-rounds", type=int, nargs="+", default=[4, 8])
    parser.add_argument("--tree-leaves", type=int, nargs="+", default=[4, 8])
    parser.add_argument("--tree-depths", type=int, nargs="+", default=[2, 3])
    parser.add_argument("--tree-learning-rate", type=float, default=0.15)
    parser.add_argument("--tree-min-child-samples", type=int, default=100)
    args = parser.parse_args()

    data = load_data("query_split", args.query_validation_fraction, args.seed)
    rows = []
    print(f"query_aware_calibration seed={args.seed}")
    for memory_kib in args.memory_kib:
        single_lbf = train_query_aware_single_lbf(data, memory_kib, args)
        plbf = train_query_aware_plbf(data, memory_kib, args)
        print_row(single_lbf)
        print_row(plbf)
        print()
        rows.extend([single_lbf, plbf])

    frame = pd.DataFrame(
        [
            {
                "memory_kib": row["memory_kib"],
                "method": row["method"],
                "fpr": row["fpr"],
                "estimated_fpr": row["estimated_fpr"],
                "time": row["construction_seconds"],
                "config": config_text(row),
            }
            for row in rows
        ]
    )
    print("summary:")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
