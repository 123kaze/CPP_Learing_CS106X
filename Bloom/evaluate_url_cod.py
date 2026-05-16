import argparse
import hashlib
import math
import pickle
import time
from pathlib import Path
from urllib.parse import urlparse

import importlib.util
import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from Bloom import FeaturePiecewiseLinearLBF


ROOT = Path(__file__).resolve().parent
RAW = ROOT / "LBF-Gama" / "dataset" / "raw"
TEACHER_BF_PATH = ROOT / "LBF-Gama" / "lbf" / "bf.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


TeacherBloomFilter = load_module("teacher_bf_original", TEACHER_BF_PATH).BloomFilter


class NumpyBloomFilter:
    def __init__(self, bit_count: int, item_count: int):
        self.bit_count = int(bit_count)
        self.hash_count = max(1, round((self.bit_count / max(1, item_count)) * math.log(2)))
        self.bits = np.zeros(self.bit_count, dtype=np.bool_)

    def _indexes(self, key):
        data = str(key).encode("utf-8", errors="ignore")
        digest = hashlib.sha256(data).digest()
        h1 = int.from_bytes(digest[:8], "little")
        h2 = int.from_bytes(digest[8:16], "little") or 1
        for i in range(self.hash_count):
            yield (h1 + i * h2) % self.bit_count

    def add(self, key):
        for index in self._indexes(key):
            self.bits[index] = True

    def contains(self, key) -> bool:
        return all(self.bits[index] for index in self._indexes(key))
“

def model_size_bits(model) -> int:
    return len(pickle.dumps(model)) * 8


def query_metrics(labels, hits):
    labels = np.asarray(labels, dtype=np.int8)
    hits = np.asarray(hits, dtype=np.bool_)
    neg = labels == 0
    pos = labels == 1
    fp = int(np.logical_and(neg, hits).sum())
    fn = int(np.logical_and(pos, ~hits).sum())
    return {
        "total": int(len(labels)),
        "negatives": int(neg.sum()),
        "positives": int(pos.sum()),
        "fp": fp,
        "fn": fn,
        "fpr_neg": fp / max(1, int(neg.sum())),
        "fnr_pos": fn / max(1, int(pos.sum())),
    }


def print_metrics(name, metrics, seconds, extra=None):
    print(f"[{name}]")
    if extra:
        for key, value in extra.items():
            print(f"  {key}: {value}")
    print(f"  construction_seconds: {seconds:.3f}")
    print(f"  total_query: {metrics['total']}")
    print(f"  negative_query: {metrics['negatives']}")
    print(f"  positive_query: {metrics['positives']}")
    print(f"  false_positives: {metrics['fp']}")
    print(f"  false_negatives: {metrics['fn']}")
    print(f"  fpr_negative_only: {metrics['fpr_neg']:.8g}")
    print(f"  fnr_positive_only: {metrics['fnr_pos']:.8g}")
    print()


def url_features(urls: pd.Series) -> np.ndarray:
    rows = []
    for raw in urls.astype(str):
        try:
            parsed = urlparse(raw if "://" in raw else "http://" + raw)
            host = parsed.netloc
            path = parsed.path
            query = parsed.query
            https = int(parsed.scheme == "https")
        except ValueError:
            host = ""
            path = raw
            query = ""
            https = 0
        rows.append(
            [
                len(raw),
                sum(c.isalpha() for c in raw),
                sum(c.isdigit() for c in raw),
                sum(not c.isalnum() for c in raw),
                raw.count("."),
                raw.count("-"),
                raw.count("/"),
                raw.count("?"),
                raw.count("="),
                https,
                len(host),
                len(path),
                len(query),
                int(any(part.isdigit() for part in host.split("."))),
            ]
        )
    return np.asarray(rows, dtype=np.float32)


def load_url(max_rows, seed):
    path = RAW / "url" / "malicious_phish.csv"
    df = pd.read_csv(path)
    df = df.drop_duplicates(subset=["url"])
    if max_rows and len(df) > max_rows:
        df = df.sample(max_rows, random_state=seed)
    y = (df["type"] != "benign").astype(np.int8).to_numpy()
    return "URL", df["url"].astype(str).to_numpy(), url_features(df["url"]), y


def load_cod(max_rows, seed):
    frames = []
    nrows = None if not max_rows else max(1, max_rows // 2)
    for name in ("train.csv", "test.csv"):
        frames.append(pd.read_csv(RAW / "cod" / name, nrows=nrows))
    df = pd.concat(frames, ignore_index=True)
    if max_rows and len(df) > max_rows:
        df = df.sample(max_rows, random_state=seed)

    y = (df["type"].astype(str).str.upper() == "STAR").astype(np.int8).to_numpy()
    keys = df["objID"].astype(str).to_numpy()
    drop_cols = [col for col in ("type", "objID") if col in df.columns]
    X = df.drop(columns=drop_cols)
    for col in X.columns:
        if not pd.api.types.is_numeric_dtype(X[col]):
            X[col] = pd.Categorical(X[col]).codes
    X = X.replace([np.inf, -np.inf], np.nan).fillna(0).to_numpy(dtype=np.float32)
    return "COD", keys, X, y


def split_dataset(keys, X, y, seed):
    train_keys, query_keys, X_train, X_query, y_train, y_query = train_test_split(
        keys, X, y, test_size=0.30, random_state=seed, stratify=y
    )
    train_keys, valid_keys, X_train, X_valid, y_train, y_valid = train_test_split(
        train_keys, X_train, y_train, test_size=0.25, random_state=seed, stratify=y_train
    )
    return train_keys, valid_keys, query_keys, X_train, X_valid, X_query, y_train, y_valid, y_query


def run_baseline(positive_keys, query_keys, y_query, total_bits):
    positives = positive_keys
    start = time.perf_counter()
    bf = TeacherBloomFilter(len(positives), total_bits)
    bf.insert(positives)
    seconds = time.perf_counter() - start
    hits = [bool(bf.test(key)) for key in query_keys]
    return query_metrics(y_query, hits), seconds, {"bits": total_bits, "positive_items": len(positives)}


def threshold_search(scores, labels, backup_bits):
    best = None
    positives = labels == 1
    negatives = labels == 0
    for threshold in np.linspace(0.01, 0.99, 99):
        backup_items = int(np.logical_and(positives, scores <= threshold).sum())
        model_fp = int(np.logical_and(negatives, scores > threshold).sum())
        backup_fpr = bloom_fpr(backup_bits, backup_items)
        expected_fp = model_fp + (int(negatives.sum()) - model_fp) * backup_fpr
        if best is None or expected_fp < best["expected_fp"]:
            best = {
                "threshold": float(threshold),
                "backup_items": backup_items,
                "expected_fp": expected_fp,
            }
    return best


def bloom_fpr(bit_count, item_count):
    if item_count <= 0:
        return 0.0
    k = max(1, round((bit_count / item_count) * math.log(2)))
    return (1.0 - math.exp(-k * item_count / bit_count)) ** k


def run_teacher_lbf(
    positive_keys,
    X_positive,
    train_keys,
    valid_keys,
    query_keys,
    X_train,
    X_valid,
    X_query,
    y_train,
    y_valid,
    y_query,
    total_bits,
    teacher_rounds,
):
    start = time.perf_counter()
    model = lgb.train(
        {
            "objective": "binary",
            "metric": "binary_logloss",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "feature_fraction": 0.9,
            "verbose": -1,
            "num_threads": 4,
            "seed": 7,
        },
        lgb.Dataset(X_train, label=y_train),
        num_boost_round=teacher_rounds,
    )
    model_bits = model_size_bits(model)
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        raise ValueError(f"memory budget too small for LightGBM model: model_bits={model_bits}")

    valid_scores = model.predict(X_valid)
    best = threshold_search(valid_scores, y_valid, backup_bits)
    backup_keys = positive_keys[model.predict(X_positive) <= best["threshold"]]
    bf = TeacherBloomFilter(len(backup_keys), backup_bits)
    bf.insert(backup_keys)
    seconds = time.perf_counter() - start

    query_scores = model.predict(X_query)
    hits = []
    for key, score in zip(query_keys, query_scores):
        hits.append(score > best["threshold"] or bool(bf.test(key)))
    return query_metrics(y_query, hits), seconds, {
        "model_bits": model_bits,
        "backup_bits": backup_bits,
        "threshold": f"{best['threshold']:.2f}",
        "backup_items": len(backup_keys),
    }


def run_student_lbf(
    positive_keys,
    X_positive,
    train_keys,
    valid_keys,
    query_keys,
    X_train,
    X_valid,
    X_query,
    y_train,
    y_valid,
    y_query,
    total_bits,
    segments,
):
    model_bits = segments * 256
    backup_bits = total_bits - model_bits
    X_negative = X_train[y_train == 0]
    X_validation_negative = X_valid[y_valid == 0]

    start = time.perf_counter()
    lbf = FeaturePiecewiseLinearLBF(maxSize=backup_bits, segmentNum=segments, threshold=0.5)
    report = lbf.train_auto(
        positive_keys=positive_keys,
        X_positive=X_positive,
        X_negative=X_negative,
        X_validation_negative=X_validation_negative,
        total_bits=total_bits,
        segment_bits=256,
    )
    seconds = time.perf_counter() - start
    hits = [lbf.contains(key, features) for key, features in zip(query_keys, X_query)]
    return query_metrics(y_query, hits), seconds, {
        "model_bits": report["model_bits"],
        "backup_bits": report["backup_bits"],
        "threshold": f"{report['threshold']:.8g}",
        "backup_positive_ratio": f"{report['backup_positive_ratio']:.8g}",
    }


def run_dataset(loader, args):
    name, keys, X, y = loader(args.max_rows, args.seed)
    total_bits = args.memory_kib * 1024 * 8
    split = split_dataset(keys, X, y, args.seed)
    train_keys, valid_keys, query_keys, X_train, X_valid, X_query, y_train, y_valid, y_query = split

    print(f"dataset={name}")
    print(f"rows={len(keys)}, positives={int(y.sum())}, negatives={int((y == 0).sum())}")
    print(f"memory_budget={args.memory_kib} KiB ({total_bits} bits)")
    print(f"split=train {len(train_keys)}, valid {len(valid_keys)}, query {len(query_keys)}")
    print()

    positive_mask = y == 1
    positive_keys = keys[positive_mask]
    X_positive = X[positive_mask]

    baseline = run_baseline(positive_keys, query_keys, y_query, total_bits)
    print_metrics("baseline BF", *baseline)

    teacher = run_teacher_lbf(
        positive_keys,
        X_positive,
        train_keys,
        valid_keys,
        query_keys,
        X_train,
        X_valid,
        X_query,
        y_train,
        y_valid,
        y_query,
        total_bits,
        args.teacher_rounds,
    )
    print_metrics("teacher LightGBM-LBF", *teacher)

    student = run_student_lbf(
        positive_keys,
        X_positive,
        train_keys,
        valid_keys,
        query_keys,
        X_train,
        X_valid,
        X_query,
        y_train,
        y_valid,
        y_query,
        total_bits,
        args.segments,
    )
    print_metrics("student PiecewiseLinearLBF", *student)

    winner = min(
        [
            ("baseline BF", baseline[0]["fpr_neg"]),
            ("teacher LightGBM-LBF", teacher[0]["fpr_neg"]),
            ("student PiecewiseLinearLBF", student[0]["fpr_neg"]),
        ],
        key=lambda item: item[1],
    )
    print(f"winner_by_negative_fpr: {winner[0]} ({winner[1]:.8g})")
    print("=" * 72)
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", nargs="+", choices=["url", "cod"], default=["url", "cod"])
    parser.add_argument("--max-rows", type=int, default=200_000)
    parser.add_argument("--memory-kib", type=int, default=320)
    parser.add_argument("--segments", type=int, default=256)
    parser.add_argument("--teacher-rounds", type=int, default=5)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    loaders = {"url": load_url, "cod": load_cod}
    for dataset in args.datasets:
        run_dataset(loaders[dataset], args)


if __name__ == "__main__":
    main()
