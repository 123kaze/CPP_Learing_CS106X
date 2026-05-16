import argparse
import time
from pathlib import Path

import numpy as np
import pandas as pd

from Bloom import FeaturePiecewiseLinearLBF


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "LBF-Gama" / "dataset"


def feature_matrix(df):
    return df.drop(columns=["url", "url_type"]).values.astype(np.float32)


def run(memory_kib, segments):
    train = pd.read_csv(DATASET / "url_train.csv")
    test = pd.read_csv(DATASET / "url_test.csv")
    query = pd.read_csv(DATASET / "url_query.csv")
    sample = pd.read_csv(DATASET / "url_sample0.1.csv")

    combined = pd.concat([train, test], ignore_index=True)
    positives = combined[combined["url_type"] == 1]
    negatives = combined[combined["url_type"] == 0]
    validation_negatives = sample[sample["url_type"] == 0]

    positive_keys = positives["url"].astype(str).to_numpy()
    X_positive = feature_matrix(positives)
    X_negative = feature_matrix(negatives)
    X_validation_negative = feature_matrix(validation_negatives)
    X_query = feature_matrix(query)
    query_keys = query["url"].astype(str).to_numpy()
    y_query = query["url_type"].to_numpy()

    total_bits = memory_kib * 1024 * 8
    model_bits = segments * 256
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        raise ValueError("memory budget is too small for configured segments")

    start = time.perf_counter()
    model = FeaturePiecewiseLinearLBF(maxSize=backup_bits, segmentNum=segments)
    report = model.train_auto(
        positive_keys=positive_keys,
        X_positive=X_positive,
        X_negative=X_negative,
        X_validation_negative=X_validation_negative,
        total_bits=total_bits,
        segment_bits=256,
    )
    seconds = time.perf_counter() - start

    fp = 0
    fn = 0
    negatives_count = 0
    positives_count = 0
    for key, features, label in zip(query_keys, X_query, y_query):
        hit = model.contains(key, features)
        if label == 0:
            negatives_count += 1
            if hit:
                fp += 1
        else:
            positives_count += 1
            if not hit:
                fn += 1

    fpr = fp / negatives_count if negatives_count else 0.0
    fnr = fn / positives_count if positives_count else 0.0
    print(f"memory_kib={memory_kib}")
    print(f"construction_seconds={seconds:.6f}")
    print(f"threshold={report['threshold']:.8g}")
    print(f"model_bits={report['model_bits']}")
    print(f"backup_bits={report['backup_bits']}")
    print(f"backup_positive_ratio={report['backup_positive_ratio']:.8g}")
    print(f"query_total={len(query)}")
    print(f"query_negatives={negatives_count}")
    print(f"query_positives={positives_count}")
    print(f"fp={fp}")
    print(f"fn={fn}")
    print(f"fpr={fpr:.12g}")
    print(f"fnr={fnr:.12g}")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--segments", type=int, default=128)
    parser.add_argument("--memory-kib", type=int, nargs="+", default=[64, 128, 192, 256, 320])
    args = parser.parse_args()

    for memory_kib in args.memory_kib:
        run(memory_kib, args.segments)


if __name__ == "__main__":
    main()
