import argparse
import heapq
import math
import pickle
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from pybloom_live import BloomFilter
from sklearn.linear_model import LogisticRegression, Ridge

try:
    import lightgbm as lgb
except ImportError:
    lgb = None


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "LBF-Gama" / "dataset"


def feature_matrix(df):
    return df.drop(columns=["url", "url_type"]).values.astype(np.float64)


def standardize_fit(X):
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    return mean, std


def standardize(X, mean, std):
    return (X - mean) / std


def sigmoid(x):
    x = np.clip(x, -40, 40)
    return 1.0 / (1.0 + np.exp(-x))


def bloom_fpr(bit_count, item_count):
    if item_count <= 0:
        return 0.0
    if bit_count <= 0:
        return 1.0
    k = max(1, round((bit_count / item_count) * math.log(2)))
    return (1.0 - math.exp(-k * item_count / bit_count)) ** k


def pybloom_error_rate(bit_count, item_count):
    if item_count <= 0:
        return 1e-8
    return max(1e-8, min(0.999999, bloom_fpr(bit_count, item_count)))


def load_data(validation_mode, query_validation_fraction, seed):
    train = pd.read_csv(DATASET / "url_train.csv")
    test = pd.read_csv(DATASET / "url_test.csv")
    query = pd.read_csv(DATASET / "url_query.csv")
    sample = pd.read_csv(DATASET / "url_sample0.1.csv")

    combined = pd.concat([train, test], ignore_index=True)
    positives = combined[combined["url_type"] == 1]
    negatives = combined[combined["url_type"] == 0]
    if validation_mode == "query_split":
        query_negatives = query[query["url_type"] == 0].sample(frac=1.0, random_state=seed)
        validation_size = int(round(len(query_negatives) * query_validation_fraction))
        validation_size = max(1, min(len(query_negatives) - 1, validation_size))
        validation_negatives = query_negatives.iloc[:validation_size]
        query = query.drop(validation_negatives.index)
    else:
        validation_negatives = sample[sample["url_type"] == 0]

    X_train = feature_matrix(combined)
    y_train = combined["url_type"].to_numpy(dtype=np.float64)

    return {
        "positive_keys": positives["url"].astype(str).to_numpy(),
        "X_positive": feature_matrix(positives),
        "X_train": X_train,
        "y_train": y_train,
        "X_validation_negative": feature_matrix(validation_negatives),
        "query_keys": query["url"].astype(str).to_numpy(),
        "X_query": feature_matrix(query),
        "y_query": query["url_type"].to_numpy(),
    }


def fit_score_model(data, model_name, c_value):
    mean, std = standardize_fit(data["X_train"])
    X_train = standardize(data["X_train"], mean, std)
    y_train = data["y_train"]

    if model_name == "logistic":
        model = LogisticRegression(C=c_value, max_iter=300, solver="lbfgs", n_jobs=1)
        model.fit(X_train, y_train)
        model_bits = (X_train.shape[1] + 1) * 64
    elif model_name == "ridge":
        model = Ridge(alpha=c_value)
        model.fit(X_train, y_train)
        model_bits = (X_train.shape[1] + 1) * 64
    elif model_name == "lighttree":
        if lgb is None:
            raise RuntimeError("lightgbm is required for --models lighttree")
        model = lgb.LGBMClassifier(
            objective="binary",
            n_estimators=int(data["tree_rounds"]),
            num_leaves=int(data["tree_leaves"]),
            max_depth=int(data["tree_depth"]),
            learning_rate=float(data["tree_learning_rate"]),
            min_child_samples=int(data["tree_min_child_samples"]),
            reg_lambda=float(c_value),
            subsample=1.0,
            colsample_bytree=1.0,
            n_jobs=1,
            random_state=int(data["seed"]),
            verbose=-1,
        )
        model.fit(X_train, y_train)
        model_bits = len(pickle.dumps(model)) * 8
    else:
        raise ValueError(f"unknown model: {model_name}")

    return model, mean, std, model_bits


def score_model(model, model_name, X, mean, std):
    X = standardize(X, mean, std)
    if model_name == "logistic":
        return model.predict_proba(X)[:, 1]
    if model_name == "lighttree":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            return model.predict_proba(X)[:, 1]
    return np.clip(model.predict(X), 0.0, 1.0)


def make_bucket_edges(scores, bucket_count):
    quantiles = np.linspace(0.0, 1.0, bucket_count + 1)
    edges = np.quantile(scores, quantiles)
    edges[0] = -np.inf
    edges[-1] = np.inf
    for i in range(1, len(edges)):
        if edges[i] <= edges[i - 1]:
            edges[i] = np.nextafter(edges[i - 1], np.inf)
    return edges


def make_adaptive_edges(positive_scores, validation_negative_scores, bucket_count, boundary_mode):
    if boundary_mode == "negative_density":
        source_scores = validation_negative_scores
    elif boundary_mode == "positive_density":
        source_scores = positive_scores
    else:
        source_scores = np.concatenate([positive_scores, validation_negative_scores])
    return make_bucket_edges(source_scores, bucket_count)


def bucket_ids(scores, edges):
    return np.searchsorted(edges[1:-1], scores, side="right")


def bucket_cost(pos_count, neg_count, total_neg, bit_count):
    weight = neg_count / total_neg
    return weight * bloom_fpr(bit_count, int(pos_count))


def allocate_bits_greedy(pos_counts, neg_counts, total_bits, step_bits):
    units = max(0, total_bits // step_bits)
    bucket_count = len(pos_counts)
    total_neg = max(1, int(np.sum(neg_counts)))
    allocation_bits = np.zeros(bucket_count, dtype=np.int64)
    heap = []

    for bucket, (p, n) in enumerate(zip(pos_counts, neg_counts)):
        current = bucket_cost(p, n, total_neg, 0)
        improved = bucket_cost(p, n, total_neg, step_bits)
        gain = current - improved
        heapq.heappush(heap, (-gain, bucket))

    for _ in range(units):
        neg_gain, bucket = heapq.heappop(heap)
        if -neg_gain <= 0:
            heapq.heappush(heap, (neg_gain, bucket))
            break
        allocation_bits[bucket] += step_bits
        current = bucket_cost(pos_counts[bucket], neg_counts[bucket], total_neg, allocation_bits[bucket])
        improved = bucket_cost(pos_counts[bucket], neg_counts[bucket], total_neg, allocation_bits[bucket] + step_bits)
        heapq.heappush(heap, (-(current - improved), bucket))

    estimated_fpr = 0.0
    for p, n, bits in zip(pos_counts, neg_counts, allocation_bits):
        estimated_fpr += bucket_cost(p, n, total_neg, int(bits))
    return allocation_bits, float(estimated_fpr)


def allocate_bits_dp(pos_counts, neg_counts, total_bits, step_bits):
    units = max(0, total_bits // step_bits)
    bucket_count = len(pos_counts)
    total_neg = max(1, int(np.sum(neg_counts)))

    costs = []
    for p, n in zip(pos_counts, neg_counts):
        weight = n / total_neg
        bucket_costs = []
        for u in range(units + 1):
            bits = u * step_bits
            fpr = bloom_fpr(bits, int(p))
            bucket_costs.append(weight * fpr)
        costs.append(np.asarray(bucket_costs, dtype=np.float64))

    dp = np.full((bucket_count + 1, units + 1), np.inf, dtype=np.float64)
    choice = np.zeros((bucket_count + 1, units + 1), dtype=np.int32)
    dp[0, 0] = 0.0

    for i in range(1, bucket_count + 1):
        c = costs[i - 1]
        for used in range(units + 1):
            prev = dp[i - 1, : used + 1]
            values = prev + c[used::-1]
            best_units = int(np.argmin(values))
            dp[i, used] = values[best_units]
            choice[i, used] = used - best_units

    best_total_units = int(np.argmin(dp[bucket_count]))
    allocation_units = np.zeros(bucket_count, dtype=np.int32)
    used = best_total_units
    for i in range(bucket_count, 0, -1):
        allocation_units[i - 1] = choice[i, used]
        used -= allocation_units[i - 1]

    return allocation_units * step_bits, float(dp[bucket_count, best_total_units])


def allocate_bits(pos_counts, neg_counts, total_bits, step_bits, allocation_method):
    if allocation_method == "dp":
        return allocate_bits_dp(pos_counts, neg_counts, total_bits, step_bits)
    return allocate_bits_greedy(pos_counts, neg_counts, total_bits, step_bits)


def interval_cost_tables(prefix_pos, prefix_neg, total_neg, max_units, step_bits):
    bin_count = len(prefix_pos) - 1
    costs = {}
    for left in range(bin_count):
        for right in range(left + 1, bin_count + 1):
            p = int(prefix_pos[right] - prefix_pos[left])
            n = int(prefix_neg[right] - prefix_neg[left])
            table = np.empty(max_units + 1, dtype=np.float64)
            for units in range(max_units + 1):
                table[units] = bucket_cost(p, n, total_neg, units * step_bits)
            costs[(left, right)] = table
    return costs


def optimize_boundary_and_bits(bin_pos, bin_neg, bucket_count, total_bits, step_bits):
    max_units = max(0, total_bits // step_bits)
    bin_count = len(bin_pos)
    total_neg = max(1, int(np.sum(bin_neg)))
    prefix_pos = np.concatenate([[0], np.cumsum(bin_pos)])
    prefix_neg = np.concatenate([[0], np.cumsum(bin_neg)])
    costs = interval_cost_tables(prefix_pos, prefix_neg, total_neg, max_units, step_bits)

    dp = np.full((bucket_count + 1, bin_count + 1, max_units + 1), np.inf, dtype=np.float64)
    prev_choice = {}
    dp[0, 0, 0] = 0.0

    for bucket in range(1, bucket_count + 1):
        for right in range(bucket, bin_count + 1):
            min_left = bucket - 1
            for left in range(min_left, right):
                prev = dp[bucket - 1, left]
                if not np.isfinite(prev).any():
                    continue
                interval_cost = costs[(left, right)]
                for used in range(max_units + 1):
                    prev_values = prev[: used + 1]
                    values = prev_values + interval_cost[used::-1]
                    local_index = int(np.argmin(values))
                    value = values[local_index]
                    if value < dp[bucket, right, used]:
                        dp[bucket, right, used] = value
                        prev_choice[(bucket, right, used)] = (left, local_index, used - local_index)

    best_units = int(np.argmin(dp[bucket_count, bin_count]))
    best_cost = float(dp[bucket_count, bin_count, best_units])
    intervals = []
    bit_units = []
    bucket = bucket_count
    right = bin_count
    used = best_units
    while bucket > 0:
        left, prev_units, interval_units = prev_choice[(bucket, right, used)]
        intervals.append((left, right))
        bit_units.append(interval_units)
        bucket -= 1
        right = left
        used = prev_units

    intervals.reverse()
    bit_units.reverse()
    return intervals, np.asarray(bit_units, dtype=np.int64) * step_bits, best_cost


class BucketBloom:
    def __init__(self, keys, bit_count):
        self.always_accept = False
        self.filter = None
        keys = [str(key) for key in keys]
        if not keys:
            return
        if bit_count <= 0:
            self.always_accept = True
            return
        self.filter = BloomFilter(capacity=len(keys), error_rate=pybloom_error_rate(bit_count, len(keys)))
        for key in keys:
            self.filter.add(key)

    def contains(self, key):
        if self.always_accept:
            return True
        if self.filter is None:
            return False
        return str(key) in self.filter


def train_plbf(
    data,
    memory_kib,
    model_name,
    c_value,
    bucket_count,
    step_bits,
    allocation_method,
    boundary_mode,
    candidate_bins,
):
    total_bits = memory_kib * 1024 * 8
    start = time.perf_counter()
    model, mean, std, model_bits = fit_score_model(data, model_name, c_value)
    metadata_bits = bucket_count * 128
    available_bits = total_bits - model_bits - metadata_bits
    if available_bits <= 0:
        return None

    positive_scores = score_model(model, model_name, data["X_positive"], mean, std)
    validation_negative_scores = score_model(model, model_name, data["X_validation_negative"], mean, std)
    if boundary_mode == "joint_dp":
        candidate_edges = make_bucket_edges(
            np.concatenate([positive_scores, validation_negative_scores]),
            candidate_bins,
        )
        positive_bins = bucket_ids(positive_scores, candidate_edges)
        validation_negative_bins = bucket_ids(validation_negative_scores, candidate_edges)
        bin_pos = np.bincount(positive_bins, minlength=candidate_bins)
        bin_neg = np.bincount(validation_negative_bins, minlength=candidate_bins)
        intervals, allocation_bits, estimated_fpr = optimize_boundary_and_bits(
            bin_pos,
            bin_neg,
            bucket_count,
            available_bits,
            step_bits,
        )
        selected_edges = [candidate_edges[0]]
        for _, right in intervals:
            selected_edges.append(candidate_edges[right])
        edges = np.asarray(selected_edges, dtype=np.float64)
        positive_buckets = bucket_ids(positive_scores, edges)
        validation_negative_buckets = bucket_ids(validation_negative_scores, edges)
        pos_counts = np.bincount(positive_buckets, minlength=bucket_count)
        neg_counts = np.bincount(validation_negative_buckets, minlength=bucket_count)
    else:
        edges = make_adaptive_edges(positive_scores, validation_negative_scores, bucket_count, boundary_mode)
        positive_buckets = bucket_ids(positive_scores, edges)
        validation_negative_buckets = bucket_ids(validation_negative_scores, edges)
        pos_counts = np.bincount(positive_buckets, minlength=bucket_count)
        neg_counts = np.bincount(validation_negative_buckets, minlength=bucket_count)

        allocation_bits, estimated_fpr = allocate_bits(
            pos_counts,
            neg_counts,
            available_bits,
            step_bits,
            allocation_method,
        )
    filters = []
    for bucket in range(bucket_count):
        keys = data["positive_keys"][positive_buckets == bucket]
        filters.append(BucketBloom(keys, int(allocation_bits[bucket])))

    construction_seconds = time.perf_counter() - start
    return {
        "model": model,
        "model_name": model_name,
        "mean": mean,
        "std": std,
        "model_bits": model_bits,
        "metadata_bits": metadata_bits,
        "available_bits": available_bits,
        "edges": edges,
        "filters": filters,
        "allocation_bits": allocation_bits,
        "pos_counts": pos_counts,
        "neg_counts": neg_counts,
        "estimated_fpr": estimated_fpr,
        "construction_seconds": construction_seconds,
        "bucket_count": bucket_count,
        "c_value": c_value,
    }


def evaluate_query(plbf, data, diagnostics_top=0):
    scores = score_model(plbf["model"], plbf["model_name"], data["X_query"], plbf["mean"], plbf["std"])
    buckets = bucket_ids(scores, plbf["edges"])
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    bucket_query_neg = np.zeros(plbf["bucket_count"], dtype=np.int64)
    bucket_fp = np.zeros(plbf["bucket_count"], dtype=np.int64)
    for key, label, bucket in zip(data["query_keys"], data["y_query"], buckets):
        hit = plbf["filters"][bucket].contains(key)
        if label == 0:
            negatives += 1
            bucket_query_neg[bucket] += 1
            if hit:
                fp += 1
                bucket_fp[bucket] += 1
        else:
            positives += 1
            if not hit:
                fn += 1
    metrics = {
        "fp": fp,
        "fn": fn,
        "negatives": negatives,
        "positives": positives,
        "fpr": fp / negatives if negatives else 0.0,
        "fnr": fn / positives if positives else 0.0,
    }
    if diagnostics_top:
        rows = []
        total_neg = max(1, negatives)
        for bucket in range(plbf["bucket_count"]):
            pos_count = int(plbf["pos_counts"][bucket])
            query_neg = int(bucket_query_neg[bucket])
            bucket_false_positive = int(bucket_fp[bucket])
            allocated_bits = int(plbf["allocation_bits"][bucket])
            rows.append(
                {
                    "bucket": bucket,
                    "score_min": plbf["edges"][bucket],
                    "score_max": plbf["edges"][bucket + 1],
                    "pos_count": pos_count,
                    "valid_neg_count": int(plbf["neg_counts"][bucket]),
                    "query_neg_count": query_neg,
                    "allocated_bits": allocated_bits,
                    "bits_per_pos": allocated_bits / pos_count if pos_count else 0.0,
                    "estimated_fpr": bloom_fpr(allocated_bits, pos_count),
                    "fp_count": bucket_false_positive,
                    "bucket_fpr": bucket_false_positive / query_neg if query_neg else 0.0,
                    "fp_contribution": bucket_false_positive / total_neg,
                }
            )
        rows.sort(key=lambda row: row["fp_contribution"], reverse=True)
        print("  top_bad_buckets:")
        for row in rows[:diagnostics_top]:
            print(
                "    "
                f"bucket={row['bucket']} "
                f"score=[{row['score_min']:.6g},{row['score_max']:.6g}) "
                f"pos={row['pos_count']} "
                f"valid_neg={row['valid_neg_count']} "
                f"query_neg={row['query_neg_count']} "
                f"bits={row['allocated_bits']} "
                f"bits_per_pos={row['bits_per_pos']:.4g} "
                f"est_fpr={row['estimated_fpr']:.6g} "
                f"fp={row['fp_count']} "
                f"bucket_fpr={row['bucket_fpr']:.6g} "
                f"contribution={row['fp_contribution']:.6g}"
            )
    return metrics


def run_memory(
    data,
    memory_kib,
    model_names,
    c_values,
    bucket_counts,
    step_bits,
    allocation_method,
    diagnostics_top,
    boundary_mode,
    candidate_bins,
):
    print(f"memory_kib={memory_kib}")
    best = None
    for model_name in model_names:
        for c_value in c_values:
            for bucket_count in bucket_counts:
                result = train_plbf(
                    data,
                    memory_kib,
                    model_name,
                    c_value,
                    bucket_count,
                    step_bits,
                    allocation_method,
                    boundary_mode,
                    candidate_bins,
                )
                if result is None:
                    continue
                print(
                    "  candidate "
                    f"model={model_name} "
                    f"C={c_value:g} "
                    f"buckets={bucket_count} "
                    f"boundary={boundary_mode} "
                    f"estimated_fpr={result['estimated_fpr']:.8g} "
                    f"model_bits={result['model_bits']} "
                    f"metadata_bits={result['metadata_bits']} "
                    f"time={result['construction_seconds']:.3f}s"
                )
                if best is None or result["estimated_fpr"] < best["estimated_fpr"]:
                    best = result

    metrics = evaluate_query(best, data, diagnostics_top)
    print(
        "  best "
        f"model={best['model_name']} "
        f"C={best['c_value']:g} "
        f"buckets={best['bucket_count']} "
        f"construction_seconds={best['construction_seconds']:.6f} "
        f"query_fp={metrics['fp']} "
        f"query_fn={metrics['fn']} "
        f"query_fpr={metrics['fpr']:.12g} "
        f"query_fnr={metrics['fnr']:.12g}"
    )
    print()
    return best, metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    parser.add_argument("--models", choices=["ridge", "logistic", "lighttree"], nargs="+", default=["logistic"])
    parser.add_argument("--c-values", type=float, nargs="+", default=[0.1, 1.0, 10.0])
    parser.add_argument("--bucket-counts", type=int, nargs="+", default=[8, 16, 32])
    parser.add_argument("--step-bits", type=int, default=4096)
    parser.add_argument("--allocation", choices=["dp", "greedy"], default="greedy")
    parser.add_argument("--diagnostics-top", type=int, default=0)
    parser.add_argument(
        "--boundary-mode",
        choices=["combined_quantile", "negative_density", "positive_density", "joint_dp"],
        default="combined_quantile",
    )
    parser.add_argument("--candidate-bins", type=int, default=32)
    parser.add_argument("--validation-mode", choices=["sample", "query_split"], default="sample")
    parser.add_argument("--query-validation-fraction", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=42)
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
    for memory_kib in args.memory_kib:
        run_memory(
            data,
            memory_kib,
            args.models,
            args.c_values,
            args.bucket_counts,
            args.step_bits,
            args.allocation,
            args.diagnostics_top,
            args.boundary_mode,
            args.candidate_bins,
        )


if __name__ == "__main__":
    main()
