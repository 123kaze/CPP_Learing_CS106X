import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round51_training_stability/src'))
import stability51 as S
from stability51 import P,W,E5,np,sha,save
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41 as E
from worker41 import bf_build,ledger
sys.path.insert(0,str(WR/'round37_clarknet_controls/src'))
import control37 as C
from types import SimpleNamespace
from contextlib import contextmanager
import json,time,resource
RA=E.RA;R6=E.R6
RECIPES=('original','balanced_clip');SEEDS=(5001,5002,5003);METHODS=('Gama','Replay','RA-global','RA6-Exact128','BF+Exact128','PlainBF','ZGate-Exact128')


def budgets(n):return tuple((int(n)*b+8191)//8192 for b in (2,4,8))

def check():
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for group in ('sources','inputs'):
        for p,h in f[group].items():assert sha(BLOOM/p)==h,p


@contextmanager
def tree_grid(available):
    original=RA.candidate_table
    def table(setup,scores,lm,kib,H,cfg):return original(setup,scores,lm,kib,H,cfg,trees=available)
    RA.candidate_table=table
    try:yield
    finally:RA.candidate_table=original


def select_all(s,scores,lm,learn,H,kib,qblob,qoff,available):
    t=time.perf_counter();g=E5.gama(E5.candidates(s,scores,kib,fracs=(0.,),trees=available));gs=time.perf_counter()-t
    t=time.perf_counter();grid=E5.candidates(s,scores,kib,trees=available);grid_s=time.perf_counter()-t
    t=time.perf_counter();rep,_=E.replay_best(grid,learn,s,qblob,qoff);replay_s=time.perf_counter()-t
    t=time.perf_counter();glob,gi=RA.select(s,scores,lm,kib,H,RA.Config(mode='global',new_mix=0.),trees=available);glob_s=time.perf_counter()-t
    t=time.perf_counter()
    with tree_grid(available):ra,ri=R6.select6(s,scores,lm,kib,H)
    ra_s=time.perf_counter()-t
    t=time.perf_counter();bc=[bf_build(s,kib*1024,f,E) for f in E5.FRACS];bf,bfp=E.replay_best(bc,learn,s,qblob,qoff);bf_s=time.perf_counter()-t
    t=time.perf_counter();rfp,_,_=E.evaluate(ra,learn,s,qblob,qoff);gate=bf if bfp<=rfp else ra;gate_s=time.perf_counter()-t
    return [('Gama',g,gs,{}),('Replay',rep,grid_s+replay_s,dict(grid_s=grid_s,learning_replay_s=replay_s,candidates=len(grid))),('RA-global',glob,glob_s,gi),('RA6-Exact128',ra,ra_s,ri),('BF+Exact128',bf,bf_s,{}),('PlainBF',bc[0],bc[0]['individual_build_s'],{}),('ZGate-Exact128',gate,ra_s+bf_s+gate_s,dict(winner='BF' if gate is bf else 'RA6',ra_learning_fp=rfp,bf_learning_fp=bfp))]


def fixed_controls(s,scores,lm,H,kib,tail,qblob,qoff,available,member_raw=None):
    M=C.M;start=time.perf_counter();anchors=E5.candidates(s,scores,kib,fracs=(.1,),trees=available);assert anchors
    anchor=min(anchors,key=lambda c:(c['structure'].est_fpr,c['trees']));st=anchor['structure'];td=E5.tree(s,scores,anchor['trees']);reg=E5.D.region_of_segment(st.b)
    mr=reg[td.seg_m].astype(np.int32);qr=reg[td.seg_q].astype(np.int32);n=np.bincount(mr,minlength=len(st.f)).astype(float);h=np.bincount(reg,weights=td.h,minlength=len(st.f));bits=int((kib*1024-td.fixed-anchor['cache_bytes'])*8)
    eps=M.capped(n,h,bits);pop=RA.population(lm,td,H,RA.Config(new_mix=0.));mass=C.region_masses(pop,td,reg,eps,anchor['slots']);identity=M.identity(n,h,mass['miss'],bits);shared_s=time.perf_counter()-start;rows=[]
    for arm in ('h','traffic','miss'):
        t=time.perf_counter();epsilon=M.capped(n,mass[arm],bits);flags,physical=M.physical(n,epsilon,s.h1m,s.h1q,mr,qr,bits);build_s=time.perf_counter()-t
        toy=dict(anchor);toy['structure']=SimpleNamespace(fp_static=flags);t=time.perf_counter();fp,state,cnt=E.evaluate(toy,tail,s,qblob,qoff);replay_s=time.perf_counter()-t
        t=time.perf_counter();hits=None
        if member_raw is not None:
            hashes,blob,offsets,midx=member_raw;spec=E.layout(anchor['cache_bytes']);before=W.ah(state);hits=int(E.member_hits(state,hashes,blob,offsets,midx,spec['buckets']));assert hits==0 and W.ah(state)==before
        member_check_s=time.perf_counter()-t
        total=int(td.fixed+anchor['cache_bytes']+physical['payload_bytes']);assert total<=kib*1024
        rows.append(dict(arm=arm,fp=fp,total_bytes=total,weights=mass[arm].tolist(),physical=physical,member_BF_FN=0,final_member_cache_hits=hits,build_s=build_s,replay_s=replay_s,all_member_cache_check_s=member_check_s))
    return dict(budget_kib=kib,trees=anchor['trees'],cache_bytes=anchor['cache_bytes'],slots=anchor['slots'],bf_bits=bits,partition=st.b.tolist(),conditional_identity=identity,actual_CLOCK_fixed_T=False,shared_prepare_s=shared_s,rows=rows)


def run(recipe,seed,pilot=False):
    check();start=time.perf_counter();name='pilot' if pilot else f'{recipe}_{seed}';dest=ROOT/f'results/{name}.json';assert not dest.exists()
    assert json.loads((WR/'round51_training_stability/results/verification.json').read_text())['gate_passes']
    if not pilot:assert json.loads((ROOT/'results/pilot_gate.json').read_text())['passed']
    t=time.perf_counter();ids,y,X,split,learn,tail,rules=P.load(seed)
    with np.load(P.ROOT/'cache/sis_fullfile.npz',allow_pickle=False) as f:blob,offsets=f['blob'],f['offsets']
    qidx=np.flatnonzero(split['neg_test']);midx=np.flatnonzero(y);qblob,qoff=E.pack([blob[offsets[i]:offsets[i+1]].tobytes() for i in qidx])
    hashes=E5.C.splitmix64(ids^np.uint64(E5.C.H1_SALT)^np.uint64(seed));s=SimpleNamespace(name=f'sis52_{recipe}_{seed}',ids=ids,y=y,split=split,h1m=hashes[y],h1q=hashes[split['neg_test']],q_ids=ids[split['neg_test']])
    load_s=time.perf_counter()-t;assert budgets(len(s.h1m))==(672,1343,2685)
    old=json.loads((P.ROOT/f'results/seed{seed}.json').read_text());assert W.ah(learn)==old['learning_sha256'] and W.ah(tail)==old['tail_sha256']
    t=time.perf_counter();train=split['member_train']|split['neg_train'];weights=S.weights(y[train]) if recipe=='balanced_clip' else None;weight_s=time.perf_counter()-t
    t=time.perf_counter();model=W.lgb.train(S.params(seed,recipe),W.lgb.Dataset(X[train],label=y[train],weight=weights),num_boost_round=200);training_s=time.perf_counter()-t
    available=tuple(n for n in E5.TREES if n<=model.num_trees());assert available and 16 in available
    t=time.perf_counter();scores=W.prefix_raw_scores(model,X,available);score_s=time.perf_counter()-t
    assert all(np.isfinite(value).all() for value in scores.values()),'Nonfinite raw scores; refuse filter construction'
    t=time.perf_counter()
    for trees in available:E5.R._MODEL_ARRAYS[s.name,trees]=W.model_arrays(model,trees)
    arrays_s=time.perf_counter()-t
    held=(y&~split['member_train'])|split['neg_val'];auc16=W.auc(y[held],scores[16][held]);r51=json.loads((WR/f'round51_training_stability/results/seed{seed}.json').read_text());ref=next(r for r in r51['rows'] if r['recipe']==recipe)
    assert np.isclose(auc16,ref['development_auc'],rtol=0,atol=1e-12)
    s.q_score=scores[max(available)][split['neg_test']]
    t=time.perf_counter()
    for trees in available:E5.tree(s,scores,trees)
    tree_s=time.perf_counter()-t
    t=time.perf_counter();lm=W.summarize19(learn);summary_s=time.perf_counter()-t
    t=time.perf_counter();warm=bf_build(s,4096,.2,E);E.evaluate(warm,learn[:2],s,qblob,qoff);E.member_hits(E.allocate(E.layout(warm['cache_bytes'])),hashes,blob,offsets,midx[:1],E.layout(warm['cache_bytes'])['buckets']);E5.D.allocate(np.ones(1000,np.int64),np.ones(1000),8000.);E5.build(s,scores,available[0],4,0.);jit_s=time.perf_counter()-t
    lengths=np.diff(qoff);out=dict(status='running',pilot=pilot,recipe=recipe,seed=seed,members=len(s.h1m),negative_pool=len(s.h1q),learning_queries=len(learn),tail_queries=len(tail),all_stable_negative_requests=63377,evaluation_pool_retained_request_fraction=(len(learn)+len(tail))/63377,learning_sha256=W.ah(learn),tail_sha256=W.ah(tail),actual_model_trees=model.num_trees(),available_tree_prefixes=available,infeasible_untrained_prefixes=[n for n in E5.TREES if n not in available],development_auc16=auc16,load_s=load_s,weight_prepare_s=weight_s,model_training_s=training_s,prefix_score_s=score_s,model_array_prepare_s=arrays_s,shared_tree_prepare_s=tree_s,summary_s=summary_s,JIT_s=jit_s,feature_payload_bytes=X.nbytes,raw_key_payload_bytes=blob.nbytes,score_arrays_payload_bytes=sum(a.nbytes for a in scores.values()),required_extra_member_index_bytes=0,query_keys_over128=int((lengths>128).sum()),tail_requests_over128=int((lengths[tail]>128).sum()),rows=[],controls=[])
    with E.exact_layout():
        for kib in ((672,) if pilot else budgets(len(s.h1m))):
            choices=select_all(s,scores,lm,learn,len(tail),kib,qblob,qoff,available)
            for method,c,select_s,info in choices:
                t=time.perf_counter();fp,data,cnt=E.evaluate(c,tail,s,qblob,qoff);replay_s=time.perf_counter()-t
                t=time.perf_counter();spec=E.layout(c['cache_bytes']);before=W.ah(data);hits=int(E.member_hits(data,hashes,blob,offsets,midx,spec['buckets']));member_s=time.perf_counter()-t
                assert hits==0 and W.ah(data)==before
                row=dict(method=method,budget_kib=kib,fp=fp,member_fn=0,cache_hits=int(cnt[3]),bypasses=int(cnt[7]),trees=c['trees'],cache_frac=c['frac'],selection_build_s=select_s,summary_charged_s=summary_s if method in ('RA-global','RA6-Exact128','ZGate-Exact128') else 0,negative_replay_s=replay_s,all_member_cache_check_s=member_s,cache_sha256=before,flags_sha256=W.ah(c['structure'].fp_static),selection_info=info,**ledger(c));out['rows'].append(row)
                print('ROW',recipe,seed,kib,method,'FP',fp,flush=True)
            ctrl=fixed_controls(s,scores,lm,len(tail),kib,tail,qblob,qoff,available,(hashes,blob,offsets,midx));out['controls'].append(ctrl);save(dest,out)
    assert len(out['rows'])==(7 if pilot else 21) and len(out['controls'])==(1 if pilot else 3)
    check();out.update(status='complete',wall_s=time.perf_counter()-start,peak_rss_bytes=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss);assert out['peak_rss_bytes']<4*1024**3;save(dest,out);print('WORKER_COMPLETE',name,out['wall_s'],flush=True)

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('recipe',choices=RECIPES);p.add_argument('seed',type=int,choices=SEEDS);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    try:run(a.recipe,a.seed,a.pilot)
    except Exception as e:save(ROOT/f'results/{"pilot" if a.pilot else a.recipe+"_"+str(a.seed)}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:300]));raise
