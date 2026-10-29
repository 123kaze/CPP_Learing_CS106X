"""Export our datasets in the input format of the original Gama scripts.

url_train.csv  = member_train + neg_train      (what our models train on)
url_test.csv   = remaining members + neg_val
url_query.csv  = neg_test pool, in the order of the query-stream indices
url_sample0.1.csv: produced exactly like LBF-Gama/dataset/get_sample.py
Columns: features..., url (key id as string), url_type (0/1).
Run with the project env (Bloom/.condaenv).
"""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / 'windows_research' / 'round2_backlog' / 'src'))
import engine as E  # noqa: E402

C = E.C


def export(ds):
    out = HERE / 'data' / ds
    out.mkdir(parents=True, exist_ok=True)
    ids, y, X, features = C.load_dataset(ds)
    sp = C.make_split(ids, y, ds)
    frame = pd.DataFrame(X, columns=[str(f) for f in features])
    frame['url'] = ids.astype(str)
    frame['url_type'] = y.astype(np.int64)
    test_members = y & ~sp['member_train']
    frame[sp['member_train'] | sp['neg_train']].to_csv(out / 'url_train.csv', index=False, float_format='%.9g')
    frame[test_members | sp['neg_val']].to_csv(out / 'url_test.csv', index=False, float_format='%.9g')
    frame[sp['neg_test']].to_csv(out / 'url_query.csv', index=False, float_format='%.9g')
    # dataset/get_sample.py, verbatim logic
    df_train = pd.read_csv(out / 'url_train.csv')
    df_test = pd.read_csv(out / 'url_test.csv')
    df_1 = pd.concat([df_train[df_train['url_type'] == 1], df_test[df_test['url_type'] == 1]])
    df_0 = pd.concat([df_train[df_train['url_type'] == 0], df_test[df_test['url_type'] == 0]])
    frac = 0.1
    df_combined = pd.concat([df_1.sample(frac=frac, random_state=42), df_0.sample(frac=frac, random_state=42)])
    df_combined.sample(frac=1, random_state=42).to_csv(out / ('url_sample' + str(frac) + '.csv'), index=False, float_format='%.9g')
    print(ds, {k: int(v.sum()) for k, v in sp.items()}, 'features', list(features), flush=True)


if __name__ == '__main__':
    for ds in sys.argv[1:]:
        export(ds)
