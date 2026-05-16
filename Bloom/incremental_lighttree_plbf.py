import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from tune_student_url_plbf import (
    BucketBloom,
    allocate_bits,
    bucket_ids,
    evaluate_query,
    feature_matrix,
    fit_score_model,
    make_adaptive_edges,
    score_model,
    train_plbf,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "LBF-Gama" / "dataset"


def split_query(query, seed, validation_fraction):
    query_negatives = query[query["url_type"] == 0].sample(frac=1.0, random_state=seed)
    validation_size = int(round(len(query_negatives) * validation_fraction))
    validation_size = max(1, min(len(query_negatives) - 1, validation_size))
    validation = query_negatives.iloc[:validation_size]
    evaluation = query.drop(validation.index)
    return validation, evaluation


def load_incremental_data(insert_fraction, seed, validation_fraction):
    train = pd.read_csv(DATASET / "url_train.csv")
    test = pd.read_csv(DATASET / "url_test.csv")
    query = pd.read_csv(DATASET / "url_query.csv")

    combined = pd.concat([train, test], ignore_index=True)
    positives = combined[combined["url_type"] == 1].sample(frac=1.0, random_state=seed)
    negatives = combined[combined["url_type"] == 0]
    validation_negatives, query_eval = split_query(query, seed, validation_fraction)

    insert_size = int(round(len(positives) * insert_fraction))
    insert_size = max(1, min(len(positives) - 1, insert_size))
    insert_pos = positives.iloc[:insert_size]
    base_pos = positives.iloc[insert_size:]
    full_pos = pd.concat([base_pos, insert_pos], ignore_index=True)

    def make_training_frame(pos):
        return pd.concat([pos, negatives], ignore_index=True)

    base_train = make_training_frame(base_pos)
    full_train = make_training_frame(full_pos)

    return {
        "base": {
            "positive_keys": base_pos["url"].astype(str).to_numpy(),
            "X_positive": feature_matrix(base_pos),
            "X_train": feature_matrix(base_train),
            "y_train": base_train["url_type"].to_numpy(dtype=np.float64),
            "X_validation_negative": feature_matrix(validation_negatives),
            "query_keys": query_eval["url"].astype(str).to_numpy(),
            "X_query": feature_matrix(query_eval),
            "y_query": query_eval["url_type"].to_numpy(),
        },
        "full": {
            "positive_keys": full_pos["url"].astype(str).to_numpy(),
            "X_positive": feature_matrix(full_pos),
            "X_train": feature_matrix(full_train),
            "y_train": full_train["url_type"].to_numpy(dtype=np.float64),
            "X_validation_negative": feature_matrix(validation_negatives),
            "query_keys": query_eval["url"].astype(str).to_numpy(),
            "X_query": feature_matrix(query_eval),
            "y_query": query_eval["url_type"].to_numpy(),
        },
        "insert_keys": insert_pos["url"].astype(str).to_numpy(),
        "X_insert": feature_matrix(insert_pos),
    }


def attach_tree_config(data, args):
    for split in ("base", "full"):
        data[split].update(
            {
                "tree_rounds": args.tree_rounds,
                "tree_leaves": args.tree_leaves,
                "tree_depth": args.tree_depth,
                "tree_learning_rate": args.tree_learning_rate,
                "tree_min_child_samples": args.tree_min_child_samples,
                "seed": args.seed,
            }
        )


def train_reserved_plbf(data, args, memory_kib):
    total_bits = memory_kib * 1024 * 8
    start = time.perf_counter()
    model, mean, std, model_bits = fit_score_model(data, "lighttree", args.c_value)
    metadata_bits = args.bucket_count * 128
    available_bits = total_bits - model_bits - metadata_bits
    if available_bits <= 0:
        raise ValueError(f"memory budget too small after model/metadata: {memory_kib} KiB")

    reserve_bits = int(round(available_bits * args.reserve_fraction))
    base_bits = max(1, available_bits - reserve_bits)

    positive_scores = score_model(model, "lighttree", data["X_positive"], mean, std)
    validation_negative_scores = score_model(model, "lighttree", data["X_validation_negative"], mean, std)
    edges = make_adaptive_edges(
        positive_scores,
        validation_negative_scores,
        args.bucket_count,
        "combined_quantile",
    )
    positive_buckets = bucket_ids(positive_scores, edges)
    validation_negative_buckets = bucket_ids(validation_negative_scores, edges)
    pos_counts = np.bincount(positive_buckets, minlength=args.bucket_count)
    neg_counts = np.bincount(validation_negative_buckets, minlength=args.bucket_count)
    allocation_bits, estimated_fpr = allocate_bits(
        pos_counts,
        neg_counts,
        base_bits,
        args.step_bits,
        "dp",
    )

    filters = []
    bucket_keys = []
    for bucket in range(args.bucket_count):
        keys = data["positive_keys"][positive_buckets == bucket]
        bucket_keys.append(keys)
        filters.append(BucketBloom(keys, int(allocation_bits[bucket])))

    construction_seconds = time.perf_counter() - start
    return {
        "model": model,
        "model_name": "lighttree",
        "mean": mean,
        "std": std,
        "model_bits": model_bits,
        "metadata_bits": metadata_bits,
        "available_bits": available_bits,
        "reserve_bits": reserve_bits,
        "edges": edges,
        "filters": filters,
        "delta_filters": [BucketBloom([], 0) for _ in range(args.bucket_count)],
        "allocation_bits": allocation_bits,
        "delta_bits": np.zeros(args.bucket_count, dtype=np.int64),
        "pos_counts": pos_counts,
        "neg_counts": neg_counts,
        "estimated_fpr": estimated_fpr,
        "construction_seconds": construction_seconds,
        "bucket_count": args.bucket_count,
        "c_value": args.c_value,
        "bucket_keys": bucket_keys,
    }


def incremental_insert(plbf, insert_keys, X_insert, args):
    start = time.perf_counter()
    scores = score_model(plbf["model"], "lighttree", X_insert, plbf["mean"], plbf["std"])
    buckets = bucket_ids(scores, plbf["edges"])
    insert_counts = np.bincount(buckets, minlength=plbf["bucket_count"])
    delta_bits, _ = allocate_bits(
        insert_counts,
        plbf["neg_counts"],
        plbf["reserve_bits"],
        args.step_bits,
        "dp",
    )

    delta_filters = []
    for bucket in range(plbf["bucket_count"]):
        keys = insert_keys[buckets == bucket]
        delta_filters.append(BucketBloom(keys, int(delta_bits[bucket])))

    updated = dict(plbf)
    updated["delta_filters"] = delta_filters
    updated["delta_bits"] = delta_bits
    updated["pos_counts"] = plbf["pos_counts"] + insert_counts
    update_seconds = time.perf_counter() - start
    return updated, update_seconds, int(np.count_nonzero(insert_counts))


def incremental_local_rebuild(plbf, insert_keys, X_insert, args):
    start = time.perf_counter()
    scores = score_model(plbf["model"], "lighttree", X_insert, plbf["mean"], plbf["std"])
    buckets = bucket_ids(scores, plbf["edges"])
    insert_counts = np.bincount(buckets, minlength=plbf["bucket_count"])
    delta_bits, _ = allocate_bits(
        insert_counts,
        plbf["neg_counts"],
        plbf["reserve_bits"],
        args.step_bits,
        "dp",
    )

    filters = list(plbf["filters"])
    bucket_keys = list(plbf["bucket_keys"])
    touched = 0
    for bucket in range(plbf["bucket_count"]):
        new_keys = insert_keys[buckets == bucket]
        if len(new_keys) == 0:
            continue
        touched += 1
        merged_keys = np.concatenate([bucket_keys[bucket], new_keys])
        bucket_keys[bucket] = merged_keys
        filters[bucket] = BucketBloom(
            merged_keys,
            int(plbf["allocation_bits"][bucket] + delta_bits[bucket]),
        )

    updated = dict(plbf)
    updated["filters"] = filters
    updated["bucket_keys"] = bucket_keys
    updated["delta_filters"] = [BucketBloom([], 0) for _ in range(plbf["bucket_count"])]
    updated["delta_bits"] = delta_bits
    updated["pos_counts"] = plbf["pos_counts"] + insert_counts
    update_seconds = time.perf_counter() - start
    return updated, update_seconds, touched


def evaluate_query_with_delta(plbf, data):
    scores = score_model(plbf["model"], "lighttree", data["X_query"], plbf["mean"], plbf["std"])
    buckets = bucket_ids(scores, plbf["edges"])
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    for key, label, bucket in zip(data["query_keys"], data["y_query"], buckets):
        hit = plbf["filters"][bucket].contains(key) or plbf["delta_filters"][bucket].contains(key)
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


def evaluate_insert_fnr(plbf, insert_keys, X_insert, use_delta):
    scores = score_model(plbf["model"], "lighttree", X_insert, plbf["mean"], plbf["std"])
    buckets = bucket_ids(scores, plbf["edges"])
    misses = 0
    for key, score, bucket in zip(insert_keys, scores, buckets):
        hit = plbf["filters"][bucket].contains(key)
        if use_delta:
            hit = hit or plbf["delta_filters"][bucket].contains(key)
        if not hit:
            misses += 1
    return misses / len(insert_keys)


def print_row(row):
    print(
        f"memory_kib={row['memory_kib']} "
        f"method={row['method']} "
        f"fpr={row['fpr']:.12g} "
        f"insert_fnr={row['insert_fnr']:.12g} "
        f"time={row['seconds']:.6f}s "
        f"extra={row['extra']}"
    )


def run_memory(data, args, memory_kib):
    rows = []

    base = train_reserved_plbf(data["base"], args, memory_kib)
    base_metrics = evaluate_query_with_delta(base, data["base"])
    base_insert_fnr = evaluate_insert_fnr(base, data["insert_keys"], data["X_insert"], use_delta=False)
    rows.append(
        {
            "memory_kib": memory_kib,
            "method": "base_no_update",
            "fpr": base_metrics["fpr"],
            "insert_fnr": base_insert_fnr,
            "seconds": base["construction_seconds"],
            "extra": f"reserve_bits={base['reserve_bits']}",
        }
    )

    inc, update_seconds, touched_buckets = incremental_insert(
        base,
        data["insert_keys"],
        data["X_insert"],
        args,
    )
    inc_metrics = evaluate_query_with_delta(inc, data["base"])
    inc_insert_fnr = evaluate_insert_fnr(inc, data["insert_keys"], data["X_insert"], use_delta=True)
    rows.append(
        {
            "memory_kib": memory_kib,
            "method": "incremental_delta",
            "fpr": inc_metrics["fpr"],
            "insert_fnr": inc_insert_fnr,
            "seconds": update_seconds,
            "extra": f"touched_buckets={touched_buckets} reserve_bits={base['reserve_bits']}",
        }
    )

    local, local_seconds, local_touched = incremental_local_rebuild(
        base,
        data["insert_keys"],
        data["X_insert"],
        args,
    )
    local_metrics = evaluate_query_with_delta(local, data["base"])
    local_insert_fnr = evaluate_insert_fnr(local, data["insert_keys"], data["X_insert"], use_delta=False)
    rows.append(
        {
            "memory_kib": memory_kib,
            "method": "incremental_local_rebuild",
            "fpr": local_metrics["fpr"],
            "insert_fnr": local_insert_fnr,
            "seconds": local_seconds,
            "extra": f"rebuilt_buckets={local_touched} reserve_bits={base['reserve_bits']}",
        }
    )

    full_start = time.perf_counter()
    full = train_plbf(
        data["full"],
        memory_kib,
        "lighttree",
        args.c_value,
        args.bucket_count,
        args.step_bits,
        "dp",
        "combined_quantile",
        32,
    )
    full_seconds = time.perf_counter() - full_start
    full_metrics = evaluate_query(full, data["full"])
    full_insert_fnr = evaluate_insert_fnr(full, data["insert_keys"], data["X_insert"], use_delta=False)
    rows.append(
        {
            "memory_kib": memory_kib,
            "method": "full_rebuild",
            "fpr": full_metrics["fpr"],
            "insert_fnr": full_insert_fnr,
            "seconds": full_seconds,
            "extra": f"model_bits={full['model_bits']}",
        }
    )

    for row in rows:
        print_row(row)
    print()
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    parser.add_argument("--insert-fraction", type=float, default=0.05)
    parser.add_argument("--validation-fraction", type=float, default=0.5)
    parser.add_argument("--reserve-fraction", type=float, default=0.10)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--c-value", type=float, default=10.0)
    parser.add_argument("--bucket-count", type=int, default=32)
    parser.add_argument("--step-bits", type=int, default=1024)
    parser.add_argument("--tree-rounds", type=int, default=8)
    parser.add_argument("--tree-leaves", type=int, default=8)
    parser.add_argument("--tree-depth", type=int, default=3)
    parser.add_argument("--tree-learning-rate", type=float, default=0.15)
    parser.add_argument("--tree-min-child-samples", type=int, default=100)
    args = parser.parse_args()

    data = load_incremental_data(args.insert_fraction, args.seed, args.validation_fraction)
    attach_tree_config(data, args)

    print(
        f"insert_fraction={args.insert_fraction} "
        f"insert_count={len(data['insert_keys'])} "
        f"reserve_fraction={args.reserve_fraction} "
        f"seed={args.seed}"
    )
    print()
    all_rows = []
    for memory_kib in args.memory_kib:
        all_rows.extend(run_memory(data, args, memory_kib))

    frame = pd.DataFrame(all_rows)
    print("summary:")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
