from pathlib import Path
import sys,json,time,os
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT.parent/'src'))
import runtime as R
import numpy as np,pandas as pd
C=R.C
C.CACHE=ROOT/'cache'
for name in ('shalla','url','caida_flow','mawi2021_flow','mawi2022_flow'):
    C.DATASETS[name]=dict(raw=ROOT/'data',member_train=.5,neg_cuts=(.1,.2))

def prepare(ds):
    folder=ROOT/'cache'/ds;folder.mkdir(exist_ok=True)
    if not (folder/'data.npz').exists():
        if ds.endswith('_flow'):
            old=ROOT.parent/'cache'/ds/'data.npz'
            if old.exists():
                with np.load(old) as data:
                    features=[str(s) for s in data['features']]
                    keep=[features.index('src'),features.index('dst')]
                    np.savez(folder/'data.npz',ids=data['ids'],y=data['y'],X=data['X'][:,keep],features=np.array(['src','dst']))
                os.link(ROOT.parent/'cache'/ds/'trace.npy',folder/'trace.npy')
            else:
                # Flow keys retain protocol identity; model input has only addresses.
                raw=pd.read_csv(ROOT/'data'/f'{ds.removesuffix("_flow")}.csv')
                flow=raw['Source'].astype(str)+'>'+raw['Destination'].astype(str)+'#'+raw['Label'].astype(str)
                codes,uniq=pd.factorize(flow,sort=False)
                first=~pd.Series(codes).duplicated().to_numpy()
                X=raw.loc[first,['Source','Destination']].to_numpy(np.float32)
                ids=pd.util.hash_pandas_object(pd.Series(uniq),index=False).to_numpy(np.uint64)
                y=raw.loc[first,'Label'].to_numpy()==1
                np.savez(folder/'data.npz',ids=ids,y=y,X=X,features=np.array(['src','dst']))
                np.save(folder/'trace.npy',codes[raw['Label'].to_numpy()==0].astype(np.int64))
        else:
            name='shalla_combined.csv' if ds=='shalla' else 'malicious_phish_full.csv'
            raw=pd.read_csv(ROOT/'data'/name)
            print(ds,'columns',raw.columns.tolist(),flush=True)
            col='url' if 'url' in raw else 'URL'
            union=None
            if ds=='url':
                label='type' if 'type' in raw else 'url_type'
                member=(raw[label].to_numpy()!=0) if raw[label].dtype.kind in 'iub' else ~raw[label].astype(str).str.lower().isin(['benign','good','0']).to_numpy()
                union=pd.DataFrame({'url':raw[col],'member':member}).groupby('url',dropna=False).member.max()
            raw=raw.drop_duplicates(col).reset_index(drop=True)
            if ds=='shalla':y=raw['label'].to_numpy()==1
            else:
                y=raw[col].map(union).to_numpy(np.bool_)
            feat=C.url_features(raw[col].astype(str));ids=pd.util.hash_pandas_object(raw[col],index=False).to_numpy(np.uint64)
            assert len(np.unique(ids))==len(ids)
            np.savez(folder/'data.npz',ids=ids,y=y,X=feat.to_numpy(np.float32),features=np.array(list(feat.columns),dtype='U'))
    return R.prepare(ds,threads=8)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('datasets',nargs='+');a=p.parse_args()
    for ds in a.datasets:prepare(ds)
