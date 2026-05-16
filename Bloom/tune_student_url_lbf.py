import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from Bloom import (
    FeaturePiecewiseLinearLBF,
    LogisticFeaturePiecewiseLinearLBF,
    MultiProjectionFeaturePiecewiseLinearLBF,
)


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "LBF-Gama" / "dataset"


def feature_matrix(df, feature_mode):
    X = df.drop(columns=["url", "url_type"]).values.astype(np.float64)
    if feature_mode == "raw":
        return X
    return augment_features(X)


def augment_features(X):
    eps = 1e-9
    url_len = np.maximum(X[:, 0], eps)
    letters = X[:, 1]
    digits = X[:, 2]
    specials = X[:, 3]
    host_len = X[:, 10] if X.shape[1] > 10 else np.zeros(len(X))
    path_len = X[:, 11] if X.shape[1] > 11 else np.zeros(len(X))
    query_len = X[:, 12] if X.shape[1] > 12 else np.zeros(len(X))

    ratios = np.column_stack(
        [
            letters / url_len,
            digits / url_len,
            specials / url_len,
            host_len / url_len,
            path_len / url_len,
            query_len / url_len,
            np.log1p(url_len),
            np.log1p(digits),
            np.log1p(specials),
        ]
    )
    return np.column_stack([X, ratios])


def load_data(feature_mode):
    train = pd.read_csv(DATASET / "url_train.csv")
    test = pd.read_csv(DATASET / "url_test.csv")
    query = pd.read_csv(DATASET / "url_query.csv")
    sample = pd.read_csv(DATASET / "url_sample0.1.csv")

    combined = pd.concat([train, test], ignore_index=True)
    positives = combined[combined["url_type"] == 1]
    negatives = combined[combined["url_type"] == 0]
    sample_negatives = sample[sample["url_type"] == 0]

    return {
        "positive_keys": positives["url"].astype(str).to_numpy(),
        "X_positive": feature_matrix(positives, feature_mode),
        "X_negative": feature_matrix(negatives, feature_mode),
        "X_validation_negative": feature_matrix(sample_negatives, feature_mode),
        "query_keys": query["url"].astype(str).to_numpy(),
        "X_query": feature_matrix(query, feature_mode),
        "y_query": query["url_type"].to_numpy(),
    }


def evaluate_query(model, query_keys, X_query, y_query):
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    for key, features, label in zip(query_keys, X_query, y_query):
        hit = model.contains(key, features)
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


def estimated_model_bits(data, segments, model_name, projection_count):
    model_bits = segments * 256
    if model_name == "multiproj":
        feature_count = data["X_positive"].shape[1]
        model_bits += projection_count * (feature_count + 1) * 64
    return model_bits


def train_candidate(data, total_bits, segments, model_name, c_value, projection_count, aggregation):
    model_bits = estimated_model_bits(data, segments, model_name, projection_count)
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        return None

    start = time.perf_counter()
    if model_name == "multiproj":
        model = MultiProjectionFeaturePiecewiseLinearLBF(
            maxSize=backup_bits,
            segmentNum=segments,
            projection_count=projection_count,
            aggregation=aggregation,
            C=c_value,
        )
    elif model_name == "logistic":
        model = LogisticFeaturePiecewiseLinearLBF(maxSize=backup_bits, segmentNum=segments, C=c_value)
    else:
        model = FeaturePiecewiseLinearLBF(maxSize=backup_bits, segmentNum=segments)
    report = model.train_auto(
        positive_keys=data["positive_keys"],
        X_positive=data["X_positive"],
        X_negative=data["X_negative"],
        X_validation_negative=data["X_validation_negative"],
        total_bits=total_bits,
        segment_bits=256,
        max_thresholds=512,
    )
    seconds = time.perf_counter() - start
    return model, report, seconds


def run_memory(data, memory_kib, segment_options, model_name, c_values, projection_counts, aggregations):
    total_bits = memory_kib * 1024 * 8
    best = None
    print(f"memory_kib={memory_kib}")

    for segments in segment_options:
        for c_value in c_values:
            for projection_count in projection_counts:
                for aggregation in aggregations:
                    if model_name != "multiproj" and (projection_count != projection_counts[0] or aggregation != aggregations[0]):
                        continue
                    result = train_candidate(
                        data,
                        total_bits,
                        segments,
                        model_name,
                        c_value,
                        projection_count,
                        aggregation,
                    )
                    if result is None:
                        continue
                    model, report, seconds = result
                    validation_fpr = report["lbf_fpr"]
                    c_text = f" C={c_value:g}" if model_name in {"logistic", "multiproj"} else ""
                    p_text = (
                        f" projections={projection_count} aggregation={aggregation}"
                        if model_name == "multiproj"
                        else ""
                    )
                    print(
                        "  candidate "
                        f"segments={segments}{c_text}{p_text} "
                        f"threshold={report['threshold']:.8g} "
                        f"estimated_fpr={validation_fpr:.8g} "
                        f"backup_ratio={report['backup_positive_ratio']:.8g} "
                        f"time={seconds:.3f}s"
                    )
                    if best is None or validation_fpr < best["report"]["lbf_fpr"]:
                        best = {
                            "segments": segments,
                            "c_value": c_value,
                            "projection_count": projection_count,
                            "aggregation": aggregation,
                            "model": model,
                            "report": report,
                            "construction_seconds": seconds,
                        }

    metrics = evaluate_query(best["model"], data["query_keys"], data["X_query"], data["y_query"])
    print(
        "  best "
        f"segments={best['segments']} "
        f"C={best['c_value']:g} "
        f"projections={best['projection_count']} "
        f"aggregation={best['aggregation']} "
        f"threshold={best['report']['threshold']:.8g} "
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
    parser.add_argument("--segments", type=int, nargs="+", default=[16, 32, 64, 128, 256, 512])
    parser.add_argument("--model", choices=["ridge", "logistic", "multiproj"], default="ridge")
    parser.add_argument("--feature-mode", choices=["raw", "url_aug"], default="url_aug")
    parser.add_argument("--c-values", type=float, nargs="+", default=[0.1, 1.0, 10.0])
    parser.add_argument("--projection-counts", type=int, nargs="+", default=[2, 4])
    parser.add_argument("--aggregations", choices=["max", "mean"], nargs="+", default=["max"])
    args = parser.parse_args()

    data = load_data(args.feature_mode)
    for memory_kib in args.memory_kib:
        run_memory(
            data,
            memory_kib,
            args.segments,
            args.model,
            args.c_values,
            args.projection_counts,
            args.aggregations,
        )


if __name__ == "__main__":
    main()
