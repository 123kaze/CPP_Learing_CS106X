import argparse
import math
import time

import numpy as np

from tune_student_url_plbf import (
    BucketBloom,
    bloom_fpr,
    load_data,
    score_model,
    train_plbf,
    fit_score_model,
)


def candidate_thresholds(positive_scores, negative_scores, max_thresholds):
    scores = np.unique(np.concatenate([positive_scores, negative_scores]))
    if len(scores) == 0:
        return np.asarray([0.5], dtype=np.float64)
    if len(scores) > max_thresholds:
        indexes = np.linspace(0, len(scores) - 1, max_thresholds).round().astype(int)
        scores = scores[indexes]
    return np.unique(np.concatenate([[0.0, 1.0, scores[-1] + 1e-12], scores]))


def train_single_threshold_lbf(data, memory_kib, args):
    total_bits = memory_kib * 1024 * 8
    start = time.perf_counter()
    model, mean, std, model_bits = fit_score_model(data, "lighttree", args.c_value)
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        return None

    positive_scores = np.sort(score_model(model, "lighttree", data["X_positive"], mean, std))
    negative_scores = np.sort(score_model(model, "lighttree", data["X_validation_negative"], mean, std))
    thresholds = candidate_thresholds(positive_scores, negative_scores, args.max_thresholds)

    best = None
    best_threshold = 0.5
    for threshold in thresholds:
        backup_items = int(np.searchsorted(positive_scores, threshold, side="left"))
        false_accepts = len(negative_scores) - int(np.searchsorted(negative_scores, threshold, side="left"))
        alpha = false_accepts / len(negative_scores)
        backup_fpr = bloom_fpr(backup_bits, backup_items)
        estimated_fpr = alpha + (1.0 - alpha) * backup_fpr
        if best is None or estimated_fpr < best:
            best = estimated_fpr
            best_threshold = float(threshold)

    positive_all_scores = score_model(model, "lighttree", data["X_positive"], mean, std)
    backup_keys = data["positive_keys"][positive_all_scores < best_threshold]
    backup = BucketBloom(backup_keys, backup_bits)
    seconds = time.perf_counter() - start
    return {
        "model": model,
        "model_name": "lighttree",
        "mean": mean,
        "std": std,
        "model_bits": model_bits,
        "backup_bits": backup_bits,
        "threshold": best_threshold,
        "backup": backup,
        "estimated_fpr": best,
        "construction_seconds": seconds,
    }


def evaluate_single_threshold(lbf, data):
    scores = score_model(lbf["model"], "lighttree", data["X_query"], lbf["mean"], lbf["std"])
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    for key, label, score in zip(data["query_keys"], data["y_query"], scores):
        hit = score >= lbf["threshold"] or lbf["backup"].contains(key)
        if label == 0:
            negatives += 1
            if hit:
                fp += 1
        else:
            positives += 1
            if not hit:
                fn += 1
    return {
        "fp": fp,
        "fn": fn,
        "negatives": negatives,
        "positives": positives,
        "fpr": fp / negatives if negatives else 0.0,
        "fnr": fn / positives if positives else 0.0,
    }


def run_method(data, memory_kib, args, method):
    if method == "single_lbf":
        result = train_single_threshold_lbf(data, memory_kib, args)
        metrics = evaluate_single_threshold(result, data)
        return result, metrics

    result = train_plbf(
        data,
        memory_kib,
        "lighttree",
        args.c_value,
        args.bucket_count,
        args.step_bits,
        "dp",
        "combined_quantile",
        32,
    )
    from tune_student_url_plbf import evaluate_query

    metrics = evaluate_query(result, data)
    return result, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    parser.add_argument("--validation-mode", choices=["sample", "query_split"], default="sample")
    parser.add_argument("--query-validation-fraction", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--c-value", type=float, default=10.0)
    parser.add_argument("--bucket-count", type=int, default=32)
    parser.add_argument("--step-bits", type=int, default=1024)
    parser.add_argument("--max-thresholds", type=int, default=512)
    parser.add_argument("--tree-rounds", type=int, default=8)
    parser.add_argument("--tree-leaves", type=int, default=8)
    parser.add_argument("--tree-depth", type=int, default=3)
    parser.add_argument("--tree-learning-rate", type=float, default=0.15)
    parser.add_argument("--tree-min-child-samples", type=int, default=100)
    args = parser.parse_args()

    data = load_data(args.validation_mode, args.query_validation_fraction, args.seed)
    data.update(
        {
            "tree_rounds": args.tree_rounds,
            "tree_leaves": args.tree_leaves,
            "tree_depth": args.tree_depth,
            "tree_learning_rate": args.tree_learning_rate,
            "tree_min_child_samples": args.tree_min_child_samples,
            "seed": args.seed,
        }
    )

    print(f"validation_mode={args.validation_mode} seed={args.seed}")
    for memory_kib in args.memory_kib:
        for method in ("single_lbf", "plbf"):
            result, metrics = run_method(data, memory_kib, args, method)
            print(
                f"memory_kib={memory_kib} "
                f"method={method} "
                f"fpr={metrics['fpr']:.12g} "
                f"fnr={metrics['fnr']:.12g} "
                f"time={result['construction_seconds']:.6f}s "
                f"estimated_fpr={result['estimated_fpr']:.12g}"
            )
        print()


if __name__ == "__main__":
    main()
