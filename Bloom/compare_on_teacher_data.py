import argparse
import importlib.util
import math
import pickle
import sys
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parent
TEACHER_ROOT = ROOT / "LBF-Gama"
TEACHER_DATASET = TEACHER_ROOT / "dataset"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


student_module = load_module("student_bloom", ROOT / "Bloom.py")
teacher_bf_module = load_module("teacher_bf", TEACHER_ROOT / "lbf" / "bf.py")

StudentLBF = student_module.PiecewiseLinearLBF
TeacherBloomFilter = teacher_bf_module.BloomFilter


def require_file(path, hint):
    if not path.exists():
        raise FileNotFoundError(f"missing {path}\n{hint}")


def load_teacher_data():
    train_path = TEACHER_DATASET / "url_train.csv"
    test_path = TEACHER_DATASET / "url_test.csv"
    query_path = TEACHER_DATASET / "url_query.csv"
    hint = (
        "Teacher URL data is required. Put url_train.csv, url_test.csv, "
        "and url_query.csv under Bloom/LBF-Gama/dataset/."
    )
    for path in (train_path, test_path, query_path):
        require_file(path, hint)

    return pd.read_csv(train_path), pd.read_csv(test_path), pd.read_csv(query_path)


def load_teacher_model(model_path):
    require_file(
        model_path,
        "Teacher LightGBM model is required. The original script expects "
        "Bloom/LBF-Gama/best_bst_20480.",
    )

    try:
        import lightgbm as lgb
    except ImportError as exc:
        raise RuntimeError("lightgbm is required to run the teacher LBF model.") from exc

    return lgb.Booster(model_file=str(model_path))


def feature_matrix(df):
    return df.drop(columns=["url", "url_type"]).values.astype("float32")


def model_size_bytes(model):
    return len(pickle.dumps(model))


def bloom_fpr(bit_count, item_count):
    if item_count <= 0:
        return 0.0
    k = max(1, round((bit_count / item_count) * math.log(2)))
    return (1.0 - math.exp(-k * item_count / bit_count)) ** k


def query_metrics(results):
    total = len(results)
    negatives = sum(1 for row in results if row["label"] == 0)
    positives = total - negatives
    fp = sum(1 for row in results if row["label"] == 0 and row["hit"])
    fn = sum(1 for row in results if row["label"] == 1 and not row["hit"])
    return {
        "total": total,
        "negatives": negatives,
        "positives": positives,
        "fp": fp,
        "fn": fn,
        "fpr_all": fp / total if total else 0.0,
        "fpr_neg": fp / negatives if negatives else 0.0,
        "fnr_pos": fn / positives if positives else 0.0,
    }


def print_metrics(name, metrics, extra=None):
    print(f"[{name}]")
    if extra:
        for key, value in extra.items():
            print(f"  {key}: {value}")
    print(f"  total query: {metrics['total']}")
    print(f"  negative query: {metrics['negatives']}")
    print(f"  positive query: {metrics['positives']}")
    print(f"  false positives: {metrics['fp']}")
    print(f"  false negatives: {metrics['fn']}")
    print(f"  fpr_all_query: {metrics['fpr_all']:.8g}")
    print(f"  fpr_negative_only: {metrics['fpr_neg']:.8g}")
    print(f"  fnr_positive_only: {metrics['fnr_pos']:.8g}")
    print()


def run_baseline_bf(positive_urls, query_df, total_bits):
    bf = TeacherBloomFilter(len(positive_urls), total_bits)
    bf.insert(positive_urls)
    rows = []
    for row in query_df.itertuples(index=False):
        rows.append({"label": int(row.url_type), "hit": bool(bf.test(row.url))})
    return query_metrics(rows)


def teacher_threshold_search(scores_df, backup_bits):
    best = None
    for i in range(1, 100):
        threshold = i / 100
        backup_urls = scores_df.loc[
            (scores_df["label"] == 1) & (scores_df["score"] <= threshold),
            "url",
        ]
        bf = TeacherBloomFilter(len(backup_urls), backup_bits)
        bf.insert(backup_urls)

        negatives = scores_df.loc[scores_df["label"] == 0]
        ml_fp = (negatives["score"] > threshold).sum()
        bf_candidates = negatives.loc[negatives["score"] <= threshold, "url"]
        bf_fp = int(bf.test(bf_candidates, single_key=False).sum())
        fp = int(ml_fp + bf_fp)
        if best is None or fp < best["fp"]:
            best = {"threshold": threshold, "fp": fp, "bf": bf, "backup_items": len(backup_urls)}
    return best


def run_teacher_lbf(train_df, test_df, query_df, model, total_bits):
    model_bits = model_size_bytes(model) * 8
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        raise ValueError(
            f"memory budget is too small: total_bits={total_bits}, "
            f"teacher_model_bits={model_bits}"
        )

    train_scores = model.predict(feature_matrix(train_df))
    test_scores = model.predict(feature_matrix(test_df))
    scores_df = pd.concat(
        [
            pd.DataFrame({"url": train_df["url"], "label": train_df["url_type"], "score": train_scores}),
            pd.DataFrame({"url": test_df["url"], "label": test_df["url_type"], "score": test_scores}),
        ],
        ignore_index=True,
    )

    best = teacher_threshold_search(scores_df, backup_bits)
    query_scores = model.predict(feature_matrix(query_df))
    rows = []
    for row, score in zip(query_df.itertuples(index=False), query_scores):
        if score > best["threshold"]:
            hit = True
        else:
            hit = bool(best["bf"].test(row.url))
        rows.append({"label": int(row.url_type), "hit": hit})

    return query_metrics(rows), {
        "model_bits": model_bits,
        "backup_bits": backup_bits,
        "threshold": f"{best['threshold']:.2f}",
        "backup_items": best["backup_items"],
    }


def run_student_lbf(train_df, test_df, query_df, total_bits, segments):
    model_bits = segments * 256
    backup_bits = total_bits - model_bits
    if backup_bits <= 0:
        raise ValueError(
            f"memory budget is too small: total_bits={total_bits}, "
            f"student_model_bits={model_bits}"
        )

    combined = pd.concat([train_df, test_df], ignore_index=True)
    positives = combined.loc[combined["url_type"] == 1, "url"].tolist()
    negatives = combined.loc[combined["url_type"] == 0, "url"].tolist()
    validation_negatives = query_df.loc[query_df["url_type"] == 0, "url"].tolist()

    lbf = StudentLBF(hashNum=1, maxSize=backup_bits, segmentNum=segments, threshold=0.5)
    report = lbf.train_auto(
        positives=positives,
        train_negatives=negatives,
        validation_negatives=validation_negatives,
        total_bits=total_bits,
        projected_items=len(positives),
        segment_bits=256,
    )

    rows = []
    for row in query_df.itertuples(index=False):
        rows.append({"label": int(row.url_type), "hit": bool(lbf.contains(row.url))})

    return query_metrics(rows), {
        "model_bits": report["model_bits"],
        "backup_bits": report["backup_bits"],
        "threshold": f"{report['threshold']:.8g}",
        "backup_positive_ratio": f"{report['backup_positive_ratio']:.8g}",
    }


def main():
    parser = argparse.ArgumentParser(
        description="Compare BF, teacher LBF, and student piecewise-linear LBF on teacher URL data."
    )
    parser.add_argument("--model", default=str(TEACHER_ROOT / "best_bst_20480"))
    parser.add_argument("--memory-kib", type=int, default=320)
    parser.add_argument("--segments", type=int, default=256)
    args = parser.parse_args()

    train_df, test_df, query_df = load_teacher_data()
    total_bits = args.memory_kib * 1024 * 8
    teacher_model = load_teacher_model(Path(args.model))

    positives = pd.concat(
        [
            train_df.loc[train_df["url_type"] == 1, "url"],
            test_df.loc[test_df["url_type"] == 1, "url"],
        ],
        ignore_index=True,
    ).tolist()

    print(f"teacher data: train={len(train_df)}, test={len(test_df)}, query={len(query_df)}")
    print(f"memory budget: {args.memory_kib} KiB ({total_bits} bits)")
    print(f"positive keys in train+test: {len(positives)}")
    print(f"theoretical BF FPR: {bloom_fpr(total_bits, len(positives)):.8g}")
    print()

    baseline = run_baseline_bf(positives, query_df, total_bits)
    print_metrics("baseline BF", baseline, {"bits": total_bits})

    teacher_metrics, teacher_extra = run_teacher_lbf(train_df, test_df, query_df, teacher_model, total_bits)
    print_metrics("teacher LightGBM-LBF", teacher_metrics, teacher_extra)

    student_metrics, student_extra = run_student_lbf(train_df, test_df, query_df, total_bits, args.segments)
    print_metrics("student PiecewiseLinearLBF", student_metrics, student_extra)

    winner = min(
        [
            ("baseline BF", baseline["fpr_neg"]),
            ("teacher LightGBM-LBF", teacher_metrics["fpr_neg"]),
            ("student PiecewiseLinearLBF", student_metrics["fpr_neg"]),
        ],
        key=lambda item: item[1],
    )
    print(f"winner_by_negative_fpr: {winner[0]} ({winner[1]:.8g})")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
