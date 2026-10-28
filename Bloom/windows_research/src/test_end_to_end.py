"""Meaningful smoke tests for live model traversal and safe feedback pipeline."""
import json
from pathlib import Path
from types import SimpleNamespace

import lightgbm as lgb
import numpy as np

import end_to_end as E
import runtime


def main():
    rng = np.random.default_rng(82)
    X = rng.normal(size=(2000, 5)).astype(np.float32)
    y = (X[:, 0] + X[:, 1] > 0)
    booster = lgb.train(dict(objective="binary", num_leaves=7, verbosity=-1, num_threads=2),
                        lgb.Dataset(X, label=y), num_boost_round=5)
    arrays = E.model_arrays(booster)
    predicted = E.predict_raw(X, *(arrays[k] for k in E.TREE_KEYS))
    ref = booster.predict(X, raw_score=True, num_threads=1)
    error = float(np.abs(predicted-ref).max())
    assert error < 1e-10
    root = Path(__file__).resolve().parents[1]
    evidence = root / "evidence" / "synthetic_end_to_end_smoke"
    evidence.mkdir(parents=True, exist_ok=True)
    model_path = evidence / "model.txt"
    booster.save_model(str(model_path))
    ids = np.arange(2000, dtype=np.uint64)
    h = runtime.C.splitmix64(ids ^ np.uint64(runtime.C.H1_SALT))
    setup = SimpleNamespace(name="synthetic_smoke", X=X, ids=ids, y=y,
                            h1m=h[y], split={"neg_test": ~y})
    # All-PASS filter makes every negative eligible and tests the feedback path.
    st = SimpleNamespace(cuts=np.empty(0), kind=np.array([0], np.uint8),
                         m=np.array([0], np.int64), k=np.array([0], np.int64),
                         bf_off=np.array([0, 0], np.int64), bits=np.empty(0, np.uint8),
                         bits_packed=True, used_bytes=12000)
    rows = E.benchmark(setup, model_path,
                       [dict(structure=st, trees=5, budget_kib=16, cache_bytes=2048)],
                       evidence, queries=10000, reps=1, workloads=("zipf1.1-10k",))
    assert all(r["false_negatives"] == 0 for r in rows)
    assert all(r["cache_hits"] > 0 and r["member_index_searches"] > 0 for r in rows)
    assert all(r["paired_false_positive_difference"] == 0 for r in rows)
    result = dict(test="synthetic component smoke, not research-dataset evidence",
                  raw_score_max_error=error, rows=len(rows),
                  false_negatives=sum(r["false_negatives"] for r in rows),
                  cache_hits=sum(r["cache_hits"] for r in rows),
                  passed=True)
    (evidence / "verification.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
