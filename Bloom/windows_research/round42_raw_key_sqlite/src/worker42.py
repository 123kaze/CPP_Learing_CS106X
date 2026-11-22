import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from online42 import *
from worker41 import bf_build
from data41 import INPUT,OUTPUT
import json,time,sqlite3,tempfile,resource,shutil
METHODS=('NoFilter','PlainBF','BF+Exact128','RA6-Exact128','RA6-prefix','DirectHashIndex','PlainBF-RAactual')
SEEDS=(3601,3602,3603);BUDGETS=(8,16,32)


def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for section in ('sources','inputs'):
        for p,h in f.get(section,{}).items():assert W.sha(BLOOM/p)==h,p
    return W.sha(ROOT/'plan/freeze.json')


def fixture(db,keys,y):
    start=time.perf_counter();con=sqlite3.connect(db)
    con.execute('PRAGMA journal_mode=OFF');con.execute('PRAGMA synchronous=OFF');con.execute('PRAGMA cache_size=-2048');con.execute('PRAGMA mmap_size=0')
    con.execute('CREATE TABLE kv(k BLOB PRIMARY KEY,v BLOB NOT NULL) WITHOUT ROWID')
    con.executemany('INSERT INTO kv VALUES(?,?)',((k,b'v'*32) for k,yes in zip(keys,y) if yes));con.commit()
    pages=con.execute('PRAGMA page_count').fetchone()[0];page_size=con.execute('PRAGMA page_size').fetchone()[0]
    con.execute('PRAGMA query_only=ON')
    return con,dict(build_s=time.perf_counter()-start,page_count=pages,page_size=page_size,file_bytes=Path(db).stat().st_size,sqlite_version=sqlite3.sqlite_version,sqlite_page_cache_limit_bytes=2097152,sqlite_mmap_bytes=0)


def prepare(seed):
    t=time.perf_counter();s,X,learn,tail=W.prepare(INPUT,seed);sp=s.split
    with np.load(OUTPUT,allow_pickle=False) as d:blob,offsets=d['blob'],d['offsets']
    keys=[blob[offsets[i]:offsets[i+1]].tobytes() for i in range(len(s.ids))]
    with np.load(INPUT,allow_pickle=False) as d:trace,order,boundary=d['trace'],d['order'],int(d['boundary'])
    keep=(s.y|sp['neg_test'])[trace];requests=trace[keep&(order>=boundary)][:200000].copy();learning=trace[keep&(order<boundary)].copy()
    hashes=E5.C.splitmix64(s.ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed))
    loading_s=time.perf_counter()-t
    t=time.perf_counter();raw_hash(b'round42-jit-only',seed);raw_hash_jit_s=time.perf_counter()-t
    t=time.perf_counter();rebuilt=np.array([raw_hash(k,seed) for k in keys],np.uint64);raw_hash_s=time.perf_counter()-t
    assert np.array_equal(rebuilt,hashes)
    t=time.perf_counter();fresh_features=np.asarray([lexical(k) for k in keys],np.float32);feature_s=time.perf_counter()-t
    assert np.array_equal(fresh_features,X)
    t=time.perf_counter();train=sp['member_train']|sp['neg_train']
    model=W.lgb.train(dict(objective='binary',num_leaves=31,learning_rate=.1,num_threads=1,seed=seed,deterministic=True,force_col_wise=True,verbose=-1),W.lgb.Dataset(X[train],label=s.y[train]),num_boost_round=200)
    training_s=time.perf_counter()-t;assert model.num_trees()==200
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,E5.TREES)
    for trees in E5.TREES:
        E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees);E5.tree(s,scores,trees)
    score_s=time.perf_counter()-t
    t=time.perf_counter();index=np.sort(s.h1m);index_s=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
    qblob,qoff=E.pack([keys[i] for i in np.flatnonzero(sp['neg_test'])])
    meta=dict(loading_s=loading_s,raw_hash_jit_s=raw_hash_jit_s,raw_hash_all_pool_s=raw_hash_s,raw_feature_extraction_all_pool_s=feature_s,model_training_s=training_s,shared_score_tree_prepare_s=score_s,index_build_s=index_s,GT_summary_s=summary_s,input_key_payload_bytes=sum(map(len,keys)),input_key_python_bytes=sys.getsizeof(keys)+sum(sys.getsizeof(k) for k in keys),feature_matrix_bytes=sys.getsizeof(X),trace_payload_bytes=requests.nbytes+learning.nbytes,source_semantics='round36 retrospective stable HTTP keys, not production KV trace')
    return s,X,learn,tail,keys,blob,offsets,requests,learning,hashes,scores,index,lm,qblob,qoff,meta


def selection(s,scores,lm,learn,tail,index,qblob,qoff,kib,reference_rows):
    out={};times={}
    with E.exact_layout():
        t=time.perf_counter();ra,info=E.R6.select6(s,scores,lm,kib,len(tail));times['RA6-Exact128']=time.perf_counter()-t
        t=time.perf_counter();bfc=[bf_build(s,kib*1024,f,E) for f in E5.FRACS];bf,_=E.replay_best(bfc,learn,s,qblob,qoff);times['BF+Exact128']=time.perf_counter()-t
        out.update({'RA6-Exact128':ra,'BF+Exact128':bf,'PlainBF':bfc[0]});times['PlainBF']=bfc[0]['individual_build_s']
    t=time.perf_counter();prefix,info=E.R6.select6(s,scores,lm,kib,len(tail));times['RA6-prefix']=time.perf_counter()-t;out['RA6-prefix']=prefix
    actual=prefix['structure'].used_bytes+(sys.getsizeof(index) if prefix['cache_bytes'] else 0)
    c=bf_build(s,actual,0.,K);out['PlainBF-RAactual']=c;times['PlainBF-RAactual']=c['individual_build_s']
    for name,c in out.items():
        ref=next(r for r in reference_rows if r['method']==name and r['base_budget_kib']==kib)
        assert c['trees']==ref['trees'] and c['frac']==ref['cache_frac'] and c['structure'].used_bytes==ref['filter_bytes'],name
        if name!='RA6-prefix':assert W.ah(c['structure'].fp_static)==ref['flags_sha256']
        else:
            safe=E5.E.CC.safe_prefix_lengths(index,s.h1q);r,_=W.evaluate(c,tail,s,safe);assert r['fp']==ref['fp']
    return out,times


def reference_for(flt,c,requests,s,hashes,blob,offsets,index):
    flags=np.ones(len(s.ids),np.bool_)
    if flt is not None:
        if flt.mode=='direct':
            p=np.searchsorted(index,hashes);flags=(p<len(index))&(index[np.minimum(p,len(index)-1)]==hashes)
        else:flags[s.split['neg_test']]=c['structure'].fp_static
    if flt is None or not flt.cache_bytes:
        spec=E.layout(0);data=np.empty(0,np.uint8);mode=1
    else:spec=flt.spec;data=(E.allocate(spec) if flt.mode=='exact' else K.allocate(spec));mode=1 if flt.mode=='exact' else 2
    mask,found=reference(requests,hashes,blob,offsets,flags,s.y,data,mode,spec['buckets'],spec.get('Q',32),spec.get('ob',0),spec.get('slot_bits',0),spec.get('handbits',0),index)
    return mask,found,data


def run(seed,pilot=False):
    frozen=check();name='pilot' if pilot else f'seed{seed}';path=ROOT/f'results/{name}.json';assert not path.exists();start=time.perf_counter()
    if not pilot:assert json.loads((ROOT/'results/pilot_gate.json').read_text())['passed']
    s,X,learn,tail,keys,blob,offsets,requests,learning,hashes,scores,index,lm,qblob,qoff,prep=prepare(seed)
    if pilot:requests=requests[:2000].copy()
    qmap=np.full(len(s.ids),-1,np.int64);qmap[s.split['neg_test']]=np.arange(len(s.h1q))
    ref41=json.loads((WR/f'round41_exact_key_budget/results/seed{seed}.json').read_text())['rows']
    t=time.perf_counter();warm=bf_build(s,4096,.2,E);E.evaluate(warm,learn[:2],s,qblob,qoff)
    safe=E5.E.CC.safe_prefix_lengths(index,s.h1q);W.evaluate(B.build(s,4,.1,K),learn[:2],s,safe)
    E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.);prep['selection_jit_warm_s']=time.perf_counter()-t
    out=dict(status='running',seed=seed,pilot=pilot,freeze_sha256=frozen,queries=len(requests),member_queries=int(s.y[requests].sum()),negative_queries=int((~s.y[requests]).sum()),requests_sha256=W.ah(requests),preparation=prep,configurations=[],timings=[],learning=[])
    assert shutil.disk_usage(ROOT).free>=2*1024**3
    with tempfile.TemporaryDirectory(prefix='raw_sqlite42_') as tmp:
        con,db=fixture(Path(tmp)/'kv.sqlite',keys,s.y);out['backend']=db;cur=con.cursor()
        try:
            for kib in ((16,) if pilot else BUDGETS):
                candidates,times=selection(s,scores,lm,learn,tail,index,qblob,qoff,kib,ref41)
                filters={};refs={}
                for method in METHODS:
                    t=time.perf_counter();c=candidates.get(method)
                    if method=='NoFilter':flt=None
                    else:
                        mode='prefix' if method=='RA6-prefix' else 'direct' if method=='DirectHashIndex' else 'exact'
                        flt=Filter(c,s,scores,mode,index)
                    filters[method]=flt;rebuild=time.perf_counter()-t
                    t=time.perf_counter()
                    # Warm JIT before timed raw queries and check every pool/member key without caching.
                    if flt is not None:
                        for ix,key in enumerate(keys):
                            decision,h,_=flt.probe(key);assert h==hashes[ix]
                            if s.y[ix]:assert decision==1
                            elif s.split['neg_test'][ix]:
                                qi=qmap[ix]
                                expected=bool(index_probe(h,index)) if method=='DirectHashIndex' else bool(c['structure'].fp_static[qi])
                                assert (decision==1)==expected,(method,ix)
                        # Warm feedback kernels and immediately discard the temporary cache contents.
                        ix=int(np.flatnonzero(s.split['neg_test'])[0]);flt.absent(hashes[ix],np.frombuffer(keys[ix],np.uint8));flt.reset()
                    refs[method]=reference_for(flt,c,requests,s,hashes,blob,offsets,index)
                    verification_s=time.perf_counter()-t
                    trained=method in ('RA6-Exact128','RA6-prefix')
                    startup=(prep['raw_feature_extraction_all_pool_s']+prep['model_training_s']+prep['shared_score_tree_prepare_s']+prep['GT_summary_s'] if trained else 0)+(prep['raw_hash_all_pool_s'] if flt is not None else 0)+times.get(method,0)+rebuild+(prep['index_build_s'] if method in ('RA6-prefix','DirectHashIndex') else 0)
                    out['configurations'].append(dict(method=method,budget_kib=kib,selection_s=times.get(method,0),executable_rebuild_s=rebuild,verification_and_JIT_s=verification_s,train_to_ready_accounted_s=startup,filter_bytes=flt.used_bytes if flt else 0,extra_index_bytes=(flt.auxiliary_bytes-flt.used_bytes) if flt else 0,auxiliary_bytes=flt.auxiliary_bytes if flt else 0,deployed_array_bytes=(flt.array_bytes+flt.cache_bytes if hasattr(flt,'array_bytes') else flt.used_bytes) if flt else 0,trees=c['trees'] if c else 0,cache_bytes=c['cache_bytes'] if c else 0))
                for rep in range(1 if pilot else 3):
                    order=METHODS[rep:]+METHODS[:rep]
                    for pos,method in enumerate(order):
                        flt=filters[method]
                        if flt is not None:flt.reset()
                        mask=np.zeros(len(requests),np.uint8);found=np.zeros_like(mask)
                        r=online(cur,keys,requests,flt,mask,found)
                        rm,rf,rd=refs[method];assert np.array_equal(mask,rm) and np.array_equal(found,rf)
                        assert r['members_found']==out['member_queries'] and r['backend_calls']==int(mask.sum()) and r['fp']==int(mask.sum()-found.sum())
                        if flt is not None:assert np.array_equal(flt.data,rd)
                        out['timings'].append(dict(method=method,budget_kib=kib,rep=rep,position=pos,**r,accepted_mask_sha256=W.ah(mask),found_mask_sha256=W.ah(found),cache_sha256=W.ah(flt.data) if flt else None,member_fn=0,reference_mask_equal=True,reference_cache_equal=True))
                        W.save(path,out);print('QUERY',seed,kib,rep,method,round(r['ns_per_query']/1000,4),'us','FP',r['fp'],flush=True)
                if not pilot and seed==3601 and kib==16:
                    cert=Filter(bf_build(s,16*1024,.1,E),s,scores,'exact')
                    neg_counts={}
                    for ix in learning:
                        if not s.y[ix]:neg_counts[keys[int(ix)]]=neg_counts.get(keys[int(ix)],0)+1
                    for rep in range(3):
                        arms=[('forced_all',None),('certified_existing_BF10',cert),('existing_BF10_no_logging',cert)]
                        if rep%2:arms.reverse()
                        for label,flt in arms:
                            if flt:flt.reset()
                            accepted=np.zeros(len(learning),np.uint8);found=np.zeros_like(accepted)
                            collect=label!='existing_BF10_no_logging'
                            r=online(cur,keys,learning,flt,accepted,found,collect=collect)
                            assert np.array_equal(found,s.y[learning].astype(np.uint8))
                            if collect:assert r['negative_distinct']==len(neg_counts) and r['negative_count_sum']==sum(neg_counts.values())
                            out['learning'].append(dict(arm=label,rep=rep,queries=len(learning),**r,all_inlet_labels_equal=True,labels_sha256=W.ah(found),requests_sha256=W.ah(learning)))
                            print('LEARNING',label,rep,r['backend_calls'],round(r['elapsed_ns']/1e9,3),flush=True)
                    W.save(path,out)
        finally:con.close()
    check();out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    W.save(path,out);print('WORKER_COMPLETE',name,len(out['timings']),out['wall_s'],flush=True)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('seed',type=int,choices=SEEDS);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    try:run(a.seed,a.pilot)
    except Exception as e:W.save(ROOT/f'results/{"pilot" if a.pilot else "seed"+str(a.seed)}.failure.json',dict(status='failed',error=repr(e)));raise
