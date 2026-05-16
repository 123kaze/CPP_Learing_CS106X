from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parent
DATASET = ROOT / "LBF-Gama" / "dataset"


def main():
    df = pd.read_csv(DATASET / "url.csv")

    positive = df[df["url_type"] == 1]
    negative = df[df["url_type"] == 0]

    negative_train_test = negative.sample(frac=0.8, random_state=42)
    train_test = pd.concat([positive, negative_train_test])
    query = negative.drop(negative_train_test.index)

    train, test = train_test_split(train_test, test_size=0.2, random_state=42)

    train.to_csv(DATASET / "url_train.csv", index=False)
    test.to_csv(DATASET / "url_test.csv", index=False)
    query.to_csv(DATASET / "url_query.csv", index=False)

    positive_all = pd.concat(
        [
            train[train["url_type"] == 1],
            test[test["url_type"] == 1],
        ]
    )
    negative_all = pd.concat(
        [
            train[train["url_type"] == 0],
            test[test["url_type"] == 0],
        ]
    )

    positive_sample = positive_all.sample(frac=0.1, random_state=42)
    negative_sample = negative_all.sample(frac=0.1, random_state=42)
    sample = pd.concat([positive_sample, negative_sample]).sample(frac=1, random_state=42)
    sample.to_csv(DATASET / "url_sample0.1.csv", index=False)

    print(f"url.csv rows={len(df)}")
    print(f"positive={len(positive)}, negative={len(negative)}")
    print(f"train={len(train)}, test={len(test)}, query={len(query)}")
    print(f"url_sample0.1={len(sample)}")


if __name__ == "__main__":
    main()
