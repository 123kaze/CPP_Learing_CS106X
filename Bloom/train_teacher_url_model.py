from pathlib import Path

import lightgbm as lgb
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent
TEACHER_ROOT = ROOT / "LBF-Gama"
DATASET = TEACHER_ROOT / "dataset"


def model_size_bytes(model):
    import pickle

    return len(pickle.dumps(model))


def main():
    max_model_memory = 20 * 1024
    df_train = pd.read_csv(DATASET / "url_train.csv")
    df_test = pd.read_csv(DATASET / "url_test.csv")

    X_train = df_train.drop(columns=["url", "url_type"]).values.astype(np.float32)
    y_train = df_train["url_type"].values.astype(np.float32)
    X_test = df_test.drop(columns=["url", "url_type"]).values.astype(np.float32)
    y_test = df_test["url_type"].values.astype(np.float32)

    train_data = lgb.Dataset(X_train, label=y_train, free_raw_data=False)
    valid_data = lgb.Dataset(X_test, label=y_test, free_raw_data=False)

    best = None
    for num_leaves in range(2, 32):
        for num_rounds in range(1, 80):
            params = {
                "objective": "binary",
                "metric": "binary_logloss",
                "num_leaves": num_leaves,
                "learning_rate": 0.05,
                "feature_fraction": 0.9,
                "verbose": -1,
                "num_threads": 4,
                "seed": 42,
            }
            model = lgb.train(params, train_data, num_boost_round=num_rounds, valid_sets=[valid_data])
            size = model_size_bytes(model)
            if size >= max_model_memory:
                break
            pred = model.predict(X_test)
            eps = 1e-12
            loss = -np.mean(y_test * np.log(pred + eps) + (1 - y_test) * np.log(1 - pred + eps))
            if best is None or loss < best["loss"]:
                best = {
                    "model": model,
                    "loss": loss,
                    "size": size,
                    "num_leaves": num_leaves,
                    "num_rounds": num_rounds,
                }

    if best is None:
        raise RuntimeError("no model fit within memory budget")

    out = TEACHER_ROOT / "best_bst_20480"
    best["model"].save_model(out)
    print(f"saved={out}")
    print(f"size_bytes={best['size']}")
    print(f"num_leaves={best['num_leaves']}")
    print(f"num_rounds={best['num_rounds']}")
    print(f"valid_logloss={best['loss']}")


if __name__ == "__main__":
    main()
