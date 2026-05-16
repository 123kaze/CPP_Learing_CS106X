import argparse
import copy
import sys
import time
from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
TEACHER_ROOT = ROOT / "LBF-Gama"
DATASET = TEACHER_ROOT / "dataset"
sys.path.insert(0, str(TEACHER_ROOT))

import lib.bf_util  # noqa: E402
import lib.lgb_url  # noqa: E402


def load_query_aware_data(seed, calibration_fraction):
    train = pd.read_csv(DATASET / "url_train.csv")
    test = pd.read_csv(DATASET / "url_test.csv")
    query = pd.read_csv(DATASET / "url_query.csv")

    query_negatives = query[query["url_type"] == 0].sample(frac=1.0, random_state=seed)
    calibration_size = int(round(len(query_negatives) * calibration_fraction))
    calibration_size = max(1, min(len(query_negatives) - 1, calibration_size))
    calibration_negatives = query_negatives.iloc[:calibration_size]
    heldout_query = query.drop(calibration_negatives.index)

    positives = pd.concat(
        [
            train[train["url_type"] == 1],
            test[test["url_type"] == 1],
        ],
        ignore_index=True,
    )

    return {
        "train": train,
        "test": test,
        "positives": positives,
        "calibration_negatives": calibration_negatives,
        "heldout_query": heldout_query,
        "X_train": train.drop(columns=["url", "url_type"]).values.astype(np.float32),
        "y_train": train["url_type"].values.astype(np.float32),
        "X_test": test.drop(columns=["url", "url_type"]).values.astype(np.float32),
        "y_test": test["url_type"].values.astype(np.float32),
        "X_positive": positives.drop(columns=["url", "url_type"]).values.astype(np.float32),
        "positive_urls": positives["url"].astype(str).tolist(),
        "X_calib_neg": calibration_negatives.drop(columns=["url", "url_type"]).values.astype(np.float32),
        "X_query": heldout_query.drop(columns=["url", "url_type"]).values.astype(np.float32),
        "y_query": heldout_query["url_type"].values.astype(np.float32),
        "query_urls": heldout_query["url"].astype(str).to_numpy(),
    }


def lightgbm_params():
    return {
        "objective": "binary",
        "metric": "binary_logloss",
        "num_leaves": 31,
        "learning_rate": 0.05,
        "feature_fraction": 0.9,
        "verbose": -1,
    }


def evaluate_lbf_thresholds(pos_scores, neg_scores, bf_bytes):
    scores = np.unique(np.concatenate([pos_scores, neg_scores]))
    if len(scores) == 0:
        return 0.5, 1.0

    pos_sorted = np.sort(pos_scores)
    neg_sorted = np.sort(neg_scores)
    best_threshold = 0.5
    best_fpr = 1.0

    for threshold in scores:
        backup_count = int(np.searchsorted(pos_sorted, threshold, side="right"))
        model_fp = len(neg_sorted) - int(np.searchsorted(neg_sorted, threshold, side="right"))
        model_fpr = model_fp / len(neg_sorted)
        backup_fpr = lib.bf_util.get_fpr(backup_count, bf_bytes)
        total_fpr = model_fpr + (1.0 - model_fpr) * backup_fpr
        if total_fpr < best_fpr:
            best_fpr = total_fpr
            best_threshold = float(threshold)

    return best_threshold, best_fpr


def build_lbf_backup(model, data, threshold, bf_bytes):
    positive_scores = model.predict(data["X_positive"])
    backup_urls = [
        url
        for url, score in zip(data["positive_urls"], positive_scores)
        if score <= threshold
    ]
    bloom_filter = lib.bf_util.create_bloom_filter(backup_urls, bf_bytes)
    return bloom_filter, len(backup_urls)


def evaluate_lbf_query(model, bloom_filter, data, threshold):
    scores = model.predict(data["X_query"])
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    for url, label, score in zip(data["query_urls"], data["y_query"], scores):
        hit = score > threshold or url in bloom_filter
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


def run_query_aware_gama_lbf(data, memory_bytes, epoch_max):
    start = time.perf_counter()
    train_data = lgb.Dataset(data["X_train"], label=data["y_train"], free_raw_data=False)
    bst = lgb.Booster(params=lightgbm_params(), train_set=train_data)

    best = None
    for epoch in range(1, epoch_max + 1):
        bst.update(train_data)
        model_size = lib.lgb_url.lgb_get_model_size(bst)
        bf_bytes = memory_bytes - model_size
        if bf_bytes <= 0:
            break

        pos_scores = bst.predict(data["X_positive"])
        neg_scores = bst.predict(data["X_calib_neg"])
        threshold, estimated_fpr = evaluate_lbf_thresholds(pos_scores, neg_scores, bf_bytes)
        if best is None or estimated_fpr < best["estimated_fpr"]:
            best = {
                "model": bst.__copy__(),
                "epoch": epoch,
                "threshold": threshold,
                "estimated_fpr": estimated_fpr,
                "model_size": model_size,
                "bf_bytes": bf_bytes,
            }

    if best is None:
        raise RuntimeError("no valid Gama-LBF model under memory budget")

    bloom_filter, backup_count = build_lbf_backup(
        best["model"],
        data,
        best["threshold"],
        best["bf_bytes"],
    )
    metrics = evaluate_lbf_query(best["model"], bloom_filter, data, best["threshold"])
    seconds = time.perf_counter() - start
    return {
        "method": "teacher_query_aware_gama_lbf",
        "epoch": best["epoch"],
        "threshold": best["threshold"],
        "estimated_fpr": best["estimated_fpr"],
        "model_size": best["model_size"],
        "bf_bytes": best["bf_bytes"],
        "backup_count": backup_count,
        "seconds": seconds,
        **metrics,
    }


def evaluate_plbf_query(plbf, model, data):
    scores = model.predict(data["X_query"])
    fp = 0
    fn = 0
    negatives = 0
    positives = 0
    for url, label, score in zip(data["query_urls"], data["y_query"], scores):
        hit = plbf.contains(url, float(score))
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


def run_query_aware_gama_plbf(data, memory_bytes, epoch_max, segments, regions):
    from plbf.FastPLBF_M import FastPLBF_M

    start = time.perf_counter()
    train_data = lgb.Dataset(data["X_train"], label=data["y_train"], free_raw_data=False)
    bst = lgb.Booster(params=lightgbm_params(), train_set=train_data)

    best = None
    for epoch in range(1, epoch_max + 1):
        bst.update(train_data)
        if epoch < 2:
            continue
        model_size = lib.lgb_url.lgb_get_model_size(bst)
        bf_bytes = memory_bytes - model_size
        if bf_bytes <= 0:
            break

        pos_scores = bst.predict(data["X_positive"]).tolist()
        neg_scores = bst.predict(data["X_calib_neg"]).tolist()
        try:
            plbf = FastPLBF_M(
                data["positive_urls"],
                pos_scores,
                neg_scores,
                float(bf_bytes * 8),
                segments,
                regions,
            )
        except ValueError:
            continue
        estimated_fpr = plbf.get_fpr()
        if best is None or estimated_fpr < best["estimated_fpr"]:
            best = {
                "model": bst.__copy__(),
                "epoch": epoch,
                "plbf": copy.deepcopy(plbf),
                "estimated_fpr": estimated_fpr,
                "model_size": model_size,
                "bf_bytes": bf_bytes,
            }

    if best is None:
        raise RuntimeError("no valid Gama-PLBF model under memory budget")

    pos_scores = best["model"].predict(data["X_positive"]).tolist()
    best["plbf"].insert_keys(data["positive_urls"], pos_scores)
    metrics = evaluate_plbf_query(best["plbf"], best["model"], data)
    seconds = time.perf_counter() - start
    return {
        "method": "teacher_query_aware_gama_plbf",
        "epoch": best["epoch"],
        "threshold": None,
        "estimated_fpr": best["estimated_fpr"],
        "model_size": best["model_size"],
        "bf_bytes": best["bf_bytes"],
        "backup_count": None,
        "seconds": seconds,
        **metrics,
    }


def print_result(memory_kib, result):
    print(
        f"memory_kib={memory_kib} "
        f"method={result['method']} "
        f"fpr={result['fpr']:.12g} "
        f"fnr={result['fnr']:.12g} "
        f"estimated_fpr={result['estimated_fpr']:.12g} "
        f"time={result['seconds']:.6f}s "
        f"epoch={result['epoch']} "
        f"model_size={result['model_size']} "
        f"bf_bytes={result['bf_bytes']} "
        f"threshold={result['threshold']} "
        f"backup_count={result['backup_count']}"
    )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    parser.add_argument("--methods", choices=["lbf", "plbf"], nargs="+", default=["lbf", "plbf"])
    parser.add_argument("--epoch-max", type=int, default=200)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--calibration-fraction", type=float, default=0.5)
    parser.add_argument("--segments", type=int, default=50)
    parser.add_argument("--regions", type=int, default=5)
    args = parser.parse_args()

    data = load_query_aware_data(args.seed, args.calibration_fraction)
    print(
        f"seed={args.seed} "
        f"calibration_negatives={len(data['X_calib_neg'])} "
        f"heldout_query={len(data['X_query'])} "
        f"positive_count={len(data['positive_urls'])}"
    )
    print()

    rows = []
    for memory_kib in args.memory_kib:
        memory_bytes = memory_kib * 1024
        if "lbf" in args.methods:
            result = run_query_aware_gama_lbf(data, memory_bytes, args.epoch_max)
            print_result(memory_kib, result)
            rows.append({"memory_kib": memory_kib, **result})
        if "plbf" in args.methods:
            result = run_query_aware_gama_plbf(
                data,
                memory_bytes,
                args.epoch_max,
                args.segments,
                args.regions,
            )
            print_result(memory_kib, result)
            rows.append({"memory_kib": memory_kib, **result})
        print()

    frame = pd.DataFrame(rows)
    print("summary:")
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
