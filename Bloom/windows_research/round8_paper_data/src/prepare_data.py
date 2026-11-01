"""Build audited data from the paper's public raw sources, not our earlier features."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import hashlib
import importlib.metadata
import json
import sys
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BLOOM = ROOT.parents[1]
REPO = BLOOM / 'original_baselines/repos/Spatio-Temporal-Lab__LBF-Gama'


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def splitmix(x):
    with np.errstate(over='ignore'):
        z = x + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def save_data(ds, frame, audit):
    out = ROOT / 'data' / ds
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'audit.json').exists():
        raise RuntimeError('Dataset already prepared; do not overwrite it')
    conflict = frame.groupby('url', sort=False)['url_type'].nunique()
    bad = conflict[conflict > 1].index
    audit['conflicting_keys_removed'] = len(bad)
    audit['conflicting_rows_removed'] = int(frame.url.isin(bad).sum())
    frame = frame[~frame.url.isin(bad)]
    audit['duplicate_key_rows_removed'] = int(frame.duplicated('url').sum())
    frame = frame.drop_duplicates('url').reset_index(drop=True)
    key = pd.util.hash_pandas_object(frame.url.astype(str), index=False).to_numpy(np.uint64)
    assert len(np.unique(key)) == len(key), 'key hash collision'
    y = frame.url_type.to_numpy(np.bool_)
    features = [c for c in frame if c not in ('url', 'url_type')]
    X = frame[features].to_numpy(np.float32)
    assert np.isfinite(X).all(), 'nonfinite input features: do not silently impute'
    u = (splitmix(key ^ np.uint64(0x5EED)) >> np.uint64(11)).astype(np.float64) / 2 ** 53
    splits = dict(member_train=y & (u < .5), neg_train=~y & (u < .1),
                  neg_val=~y & (u >= .1) & (u < .2), neg_test=~y & (u >= .2))
    np.savez(out / 'data.npz', ids=key, y=y, X=X, features=np.array(features), **splits)
    train = splits['member_train'] | splits['neg_train']
    test = (y & ~splits['member_train']) | splits['neg_val']
    for name, mask in (('url_train.csv', train), ('url_test.csv', test), ('url_query.csv', splits['neg_test'])):
        frame[mask].to_csv(out / name, index=False, float_format='%.9g')
    known = frame[train | test]
    sample = pd.concat([known[known.url_type == 1].sample(frac=.1, random_state=42),
                        known[known.url_type == 0].sample(frac=.1, random_state=42)])
    sample.sample(frac=1, random_state=42).to_csv(out / 'url_sample0.1.csv', index=False, float_format='%.9g')
    audit.update(dataset=ds, final_rows=len(frame), members=int(y.sum()), negatives=int((~y).sum()),
                 features=features, split={k:int(v.sum()) for k,v in splits.items()},
                 data_sha256=sha(out / 'data.npz'), status='public_source_reconstruction_not_exact_paper_split')
    (out / 'audit.json').write_text(json.dumps(audit, indent=2, ensure_ascii=False) + '\n')
    print(json.dumps(audit, ensure_ascii=False), flush=True)


def url():
    sys.path.insert(0, str(ROOT / 'deps'))
    import tldextract
    tldextract.extract = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=str(ROOT / 'data' / 'suffix_cache'))
    raw = BLOOM / 'windows_research/round2_backlog/data/malicious_phish_full.csv'
    source_file = REPO / 'embedding_gene/url_embedding.py'
    folder = ROOT / 'data' / 'url_features'
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / 'url.csv'
    if target.exists():
        raise RuntimeError('Author feature output already exists; do not overwrite')
    source = source_file.read_text()
    source = source.replace("pd.read_csv('../dataset/malicious_phish.csv')", f'pd.read_csv({str(raw)!r})')
    source = source.replace("data.to_csv('../dataset/url.csv', index=False)", f'data.to_csv({str(target)!r}, index=False)')
    exec(compile(source, str(source_file), 'exec'), {'__name__': '__main__'})
    original = pd.read_csv(raw)
    transformed = pd.read_csv(target)
    audit = dict(raw_source='https://www.kaggle.com/datasets/sid321axn/malicious-urls-dataset',
                 raw_version=1, raw_sha256=sha(raw), raw_bytes=raw.stat().st_size,
                 raw_rows=len(original), raw_labels=original.type.value_counts().to_dict(),
                 paper_members=223088, paper_negatives=428118,
                 author_feature_rows=len(transformed), author_feature_labels=transformed.url_type.value_counts().to_dict(),
                 feature_source_sha256=sha(source_file), suffix_snapshot='tldextract bundled offline snapshot',
                 dependencies={m:importlib.metadata.version(m) for m in ('tld', 'tldextract')})
    save_data('paper_url', transformed, audit)


def cod():
    files = [BLOOM / 'LBF-Gama/dataset/raw/cod' / name for name in ('train.csv', 'test.csv')]
    counts, missing = {}, {}
    frames = []
    for path in files:
        for chunk in pd.read_csv(path, chunksize=100000, dtype={'objID':np.uint64, 'type':'category'}):
            for label, count in chunk.type.value_counts().items():
                counts[str(label)] = counts.get(str(label), 0) + int(count)
            invalid = chunk.isna().any(axis=1)
            for label, count in chunk.loc[invalid, 'type'].value_counts().items():
                missing[str(label)] = missing.get(str(label), 0) + int(count)
            if invalid.any():
                raise ValueError(f'Raw COD has missing values: {missing}; need declared preprocessing')
            frames.append(chunk)
    data = pd.concat(frames, ignore_index=True)
    assert set(data.type.unique()) == {'galaxy', 'star'}
    data['url_type'] = (data.type == 'galaxy').astype(np.int8)
    data = data.drop(columns='type').rename(columns={'objID':'url'})
    audit = dict(raw_source='https://www.kaggle.com/datasets/hari31416/celestialclassify', raw_version=1,
                 raw_files=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p)) for p in files],
                 raw_labels=counts, missing_by_label=missing, paper_members=2498077, paper_negatives=2980291,
                 feature_policy='Original numeric columns except objID (key); no undocumented count-matching sample')
    save_data('paper_cod', data, audit)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('dataset', choices=('url', 'cod'))
    (url if p.parse_args().dataset == 'url' else cod)()
