import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent
sys.path.insert(0,str(WR/'round44_trace_snapshot/src'))
import data44 as D
from data44 import W,np,sha,save
from collections import Counter
import json,time
LENGTHS=(1,2,4,8);SLOTS=16;PAYLOAD=32+16*sum(n+1 for n in LENGTHS)


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in f[section].items():assert sha(BLOOM/p)==h,p


def vocabulary(keys):
    if len(set(keys))!=len(keys):raise ValueError('Vocabularyinput must be distinct training keys')
    data=np.zeros(PAYLOAD,np.uint8);data[:4]=np.frombuffer(b'NS45',np.uint8);base=32
    for group,n in enumerate(LENGTHS):
        counts=Counter(k[:n] for k in keys if len(k)>=n)
        ordered=sorted(counts,key=lambda k:(-counts[k],k))[:SLOTS];data[8+group]=len(ordered)
        for i,prefix in enumerate(ordered):
            p=base+i*(n+1);data[p]=1;data[p+1:p+1+n]=np.frombuffer(prefix,np.uint8)
        base+=SLOTS*(n+1)
    assert base==len(data) and data.flags.owndata
    return data


def encode(keys,data):
    out=np.zeros((len(keys),64),np.float32);base=32
    for group,n in enumerate(LENGTHS):
        # Local decoding workspaces are feature-preparation temporaries, not hidden deployed dictionaries.
        lookup={data[base+i*(n+1)+1:base+i*(n+1)+1+n].tobytes():i for i in range(SLOTS) if data[base+i*(n+1)]}
        for row,key in enumerate(keys):
            if len(key)>=n:
                col=lookup.get(key[:n])
                if col is not None:out[row,group*SLOTS+col]=1
        base+=SLOTS*(n+1)
    return out


def run(cluster):
    check();start=time.perf_counter();dest=ROOT/f'results/{cluster}.json';assert not dest.exists()
    old=WR/'round44_trace_snapshot';path=old/f'cache/{cluster}.npz'
    with np.load(path,allow_pickle=False) as z:
        ids,y,first,trace,le,blob,offsets=[z[k] for k in ('ids','y','first','trace','learn_end','blob','offsets')]
    le=int(le);dev=np.flatnonzero(first<le);keys=[blob[offsets[i]:offsets[i+1]].tobytes() for i in dev]
    mapping={k:i for i,k in enumerate(keys)};sizes=np.full(len(keys),-1,np.int64);order=0
    t=time.perf_counter()
    with (old/f'inputs/{cluster}/trace.csv').open('rb') as f:
        while order<le:
            line=f.readline(65537)
            if not line:raise ValueError('Input ended before frozen learning boundary')
            _,key,size,op=D.decode(line)
            if op not in ('get','gets'):continue
            ix=mapping[key];global_index=int(dev[ix]);assert global_index==int(trace[order])
            if sizes[ix]<0:sizes[ix]=size
            else:assert sizes[ix]==size,'Original query key_size inconsistent'
            order+=1
    assert (sizes>=0).all();recover_s=time.perf_counter()-t
    reference=json.loads((old/f'results/{cluster}_qualification.json').read_text())
    out=dict(status='running',cluster=cluster,known_exploration_dataset=True,new_holdout=False,development_key_count=len(dev),GET_prefix_read=le,raw_metadata_recovery_s=recover_s,key_size_payload_bytes=sizes.nbytes,rows=[])
    for seed in D.SEEDS:
        s,X,_,_=D.prepare(path,seed);sp=s.split;train=(sp['member_train']|sp['neg_train'])[dev];validation=((s.y&~sp['member_train'])|sp['neg_val'])[dev];labels=s.y[dev]
        assert not np.any(train&validation);assert np.all(first[dev[train|validation]]<le)
        t=time.perf_counter();vocab=vocabulary([k for k,use in zip(keys,train) if use]);vocab_s=time.perf_counter()-t
        t=time.perf_counter();ns=encode(keys,vocab);ns_s=time.perf_counter()-t;lex=X[dev].copy();size=sizes.astype(np.float32).reshape(-1,1)
        variants={'lexical24':lex,'key_size25':np.column_stack((lex,size)),'prefix88':np.column_stack((lex,ns)),'combined89':np.column_stack((lex,size,ns))}
        ref=next(r for r in reference['diagnostics'] if r['seed']==seed)
        for name,features in variants.items():
            t=time.perf_counter();model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(features[train],label=labels[train]),num_boost_round=16);training_s=time.perf_counter()-t
            t=time.perf_counter();score=model.predict(features[validation],raw_score=True,num_threads=1);score_s=time.perf_counter()-t
            t=time.perf_counter();auc=W.auc(labels[validation],score);auc_s=time.perf_counter()-t
            if name=='lexical24':assert np.isclose(auc,ref['development_auc16'],rtol=0,atol=1e-12)
            ns_used=name in ('prefix88','combined89')
            row=dict(seed=seed,representation=name,dimensions=features.shape[1],development_auc=auc,model_trees=model.num_trees(),vocab_allocated_bytes=sys.getsizeof(vocab) if ns_used else 0,vocab_payload_bytes=vocab.nbytes if ns_used else 0,vocab_valid_slots=[int(x) for x in vocab[8:12]] if ns_used else [],vocab_sha256=W.ah(vocab) if ns_used else None,vocab_build_s=vocab_s if ns_used else 0,namespace_encode_s=ns_s if ns_used else 0,feature_matrix_payload_bytes=features.nbytes,training_s=training_s,score_s=score_s,auc_s=auc_s,training_keys=int(train.sum()),validation_keys=int(validation.sum()),tail_FP_measured=False)
            out['rows'].append(row);save(dest,out);print('DEV_AUC',cluster,seed,name,auc,flush=True)
    check();out.update(status='complete',wall_s=time.perf_counter()-start);save(dest,out)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('cluster',choices=D.CLUSTERS);a=p.parse_args()
    try:run(a.cluster)
    except Exception as e:save(ROOT/f'results/{a.cluster}.failure.json',dict(status='failed',error=repr(e)));raise
