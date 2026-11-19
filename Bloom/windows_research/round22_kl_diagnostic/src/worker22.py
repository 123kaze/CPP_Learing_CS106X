"""Deferred real-data worker. Never imported by prepare or small unit tests."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from control22 import ROOT, WR, BLOOM, digest, save, protocol, require_cached, cache_files, verify_freeze
import argparse
import hashlib
import json
import time
import traceback


def write_guard():
    """Defense in depth: Python-level writes must remain within the new round."""
    write_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND
    def allowed(p):
        if isinstance(p, int) or p is None:
            return
        if not Path(os.fsdecode(p)).resolve().is_relative_to(ROOT):
            raise PermissionError('Round22 refuses writes outside its directory: ' + str(p))
    def audit(event, args):
        if event == 'open':
            path, mode, flags = args
            if (isinstance(mode, str) and any(c in mode for c in 'wax+')) or (flags & write_flags):
                allowed(path)
        elif event in ('os.mkdir', 'os.remove', 'os.rmdir', 'os.unlink'):
            allowed(args[0])
        elif event in ('os.rename', 'os.replace'):
            allowed(args[0]); allowed(args[1])
    sys.addaudithook(audit)


def check_ticket(path):
    path = Path(path).resolve()
    if not path.is_relative_to(ROOT / 'results'):
        raise ValueError('A runner-issued ticket in round22/results is required')
    ticket = json.loads(path.read_text())
    if not (ticket.get('status') == 'authorized' and
            ticket.get('token') == os.environ.get('ROUND22_RUN_TOKEN') and
            ticket.get('source_freeze_sha256') == verify_freeze()):
        raise RuntimeError('Missing or stale runner authorization ticket')
    return ticket


def identity(c):
    st = c['structure']
    return dict(trees=c['trees'], frac=c['frac'], cache_bytes=c['cache_bytes'],
                total_bytes=int(st.used_bytes), model_bytes=int(st.model_bytes),
                static_flags_sha256=hashlib.sha256(memoryview(st.fp_static).cast('B')).hexdigest())


def main(a):
    ticket = check_ticket(a.ticket)  # Must precede any scientific/frozen import.
    output = Path(a.output).resolve()
    if not output.is_relative_to(ROOT / 'results') or output.exists():
        raise ValueError('Output must be a fresh file inside round22/results')
    write_guard()
    out = dict(status='running', dataset=a.dataset, heuristic_enabled=ticket['heuristic'], cases=[])
    start = time.perf_counter()
    try:
        import numpy as np
        import lightgbm as lgb
        from numba import get_num_threads
        from math22 import A, fit_eb, theory_layers, integer_fpr
        assert get_num_threads() == 1
        # Importing the frozen entry points is only allowed after the runner gate.
        for rel in ('round17_zerotree/src', 'round19_gt_fix/src', 'round20_zero_guard/src'):
            sys.path.insert(0, str(WR / rel))
        import zero17 as Z
        from entry19 import patched, ORIGINAL_SUMMARIZE
        from summarize19 import summarize19
        E5, RA, BF, RA6 = Z.E5, Z.RA, Z.BF, Z.ra6
        E5.K = BF.CACHES['index']
        if a.dataset.endswith('_tcp_flow'):
            sys.path.insert(0, str(WR / 'round11_tcp/src'))
            import tcp11  # registry only, never call prepare()
        cfg = protocol()
        assert tuple(E5.FRACS) == tuple(cfg['zero_cache_fractions'])
        assert set(cfg['static_tree_prefixes']).issubset(E5.TREES)
        require_cached(a.dataset)
        # Hash existing large files only now, never during prepare/tests.
        out['inputs'] = {str(p.relative_to(BLOOM)): digest(p) for p in cache_files(a.dataset)}
        def forbidden_training(*args, **kwargs):
            raise RuntimeError('Training is forbidden in round22; prepared caches required')
        lgb.train = forbidden_training
        t = time.perf_counter()
        setup, scores, safe = E5.load(a.dataset)
        out['shared_input_prepare_s'] = time.perf_counter()-t
        out['environment'] = dict(python=sys.version, numpy=np.__version__, numba_threads=get_num_threads(),
                                  native_env={k:os.environ.get(k) for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','NUMBA_NUM_THREADS')})
        specs = {'真实轨迹':None} if a.dataset.endswith('_flow') else dict(E5.workload_specs(len(setup.h1q)))
        indexes = [i for i in ticket['case_indexes'] if cfg['matrix'][i]['dataset'] == a.dataset]
        for ci in indexes:
            case = cfg['matrix'][ci]
            kib, name = case['budget_kib'], case['workload']
            print('START CASE', ci, a.dataset, kib, name, flush=True)
            t = time.perf_counter()
            stream = E5.base_stream(setup, name, specs[name], cfg['seed'], cfg['synthetic_queries'])
            learn, tail = stream[:len(stream)//4], stream[len(stream)//4:]
            assert len(learn) > 0 and len(tail) > 0
            stream_s = time.perf_counter()-t
            H = len(tail)  # Horizon only, no evaluation counts enter selection.
            selection_start = time.perf_counter()
            phase = {}
            t = time.perf_counter(); lm_old = ORIGINAL_SUMMARIZE(learn,True)
            phase['original_statistics_s'] = time.perf_counter()-t
            t = time.perf_counter(); lm = summarize19(learn,True)
            phase['GT19_statistics_s'] = time.perf_counter()-t
            assert lm.N1 == lm_old.N1
            same_stats = np.array_equal(lm.rate, lm_old.rate)
            t = time.perf_counter(); zero_rows = Z.zero_table(setup,lm,kib,H)
            phase['zero13_prediction_s'] = time.perf_counter()-t
            assert len(zero_rows) == 13
            plain_bits = next(r['bf_bits'] for r in zero_rows if r['frac'] == 0)
            rows, built, fits, skipped = [], [], {}, []
            tree_prepare_s = alpha_s = mass_s = static_build_s = static_analysis_s = 0.
            def region_record(c, td, mass, family, alpha=None, external_T=0.):
                st = c['structure']; reg = E5.D.region_of_segment(st.b)
                nr = len(st.f)
                agg = lambda x: np.bincount(reg,weights=np.asarray(x,float),minlength=nr)
                n = agg(td.g); q = agg(td.h); M = agg(mass)
                p_dp = agg((td.g+1)/(td.g.sum()+len(td.g)))
                avail = float((kib*1024-td.fixed-c['cache_bytes'])*8)
                physical_bits = int(st.m.sum())
                eps_int = integer_fpr(n,st.m,st.k)
                eps_dp = agg(st.seg_fpr_cont)/np.bincount(reg,minlength=nr)
                rec = dict(family=family,identity=identity(c),alpha=alpha,
                    region_bounds_microbins=st.b.tolist(),n=n.tolist(),p=(n/n.sum()).tolist(),
                    p_DP_smoothed=p_dp.tolist(),q=q.tolist(),M=M.tolist(),W=float(M.sum()),
                    r=(M/M.sum()).tolist() if M.sum()>0 else None,
                    bloom_available_bits=avail,bloom_logical_bits=physical_bits,
                    bloom_array_bits=int(st.filter_bytes)*8,
                    model_bytes=int(st.model_bytes),metadata_bytes=int(st.metadata_bytes),
                    array_overhead_bytes=int(st.array_overhead_bytes),cache_bytes=c['cache_bytes'],
                    total_bytes=int(st.used_bytes),budget_bytes=kib*1024,
                    unused_bytes=kib*1024-int(st.used_bytes),epsilon_DP_continuous=eps_dp.tolist(),
                    epsilon_integer_ideal=eps_int.tolist(),m=st.m.tolist(),k=st.k.tolist(),
                    kind=st.kind.tolist(),kind_codes=dict(PASS=int(E5.C.PASS),BF=int(E5.C.BF),EMPTY=int(E5.C.EMPTY)),
                    predicted_integer_FP=float(M@eps_int),T=external_T,
                    T_note='external T=0; cache absent' if external_T == 0 else 'not a shared scalar: candidate-dependent Che/set-associative mixture; RA6 bucket refinement differs',
                    miss_source='GT19 learning-rate T=0 proxy' if external_T == 0 else 'post-build GT population effective misses, not the exact selected bucket objective')
                assert rec['total_bytes'] <= kib*1024
                if external_T == 0:
                    rec['A_B_available_budget'] = theory_layers(n,M,q,avail,plain_bits)
                    rec['A_B_logical_deployed_budget'] = theory_layers(n,M,q,physical_bits,plain_bits)
                return rec
            for tree in cfg['static_tree_prefixes']:
                t = time.perf_counter(); td = E5.tree(setup,scores,tree);tree_prepare_s += time.perf_counter()-t
                if td.fixed >= kib*1024:
                    skipped.append(dict(trees=tree,reason='fixed physical cost >= total budget'))
                    continue
                t = time.perf_counter()
                seg = td.seg_q[lm.keys]
                singleton = np.bincount(seg[lm.counts==1],minlength=len(td.g))
                seen = np.bincount(seg,weights=H*lm.rate,minlength=len(td.g))
                unseen_total = H*lm.N1/lm.L
                M_h = seen + unseen_total*td.h
                mass_s += time.perf_counter()-t
                t = time.perf_counter(); u, eb = fit_eb(singleton,td.h,cfg['EB']); alpha_s += time.perf_counter()-t
                M_eb = seen + unseen_total*u
                fits[str(tree)] = dict(**eb,singletons=singleton.tolist(),h=td.h.tolist(),
                                       posterior_mean=u.tolist(),all_learning_keys_singleton=bool(np.all(lm.counts==1)))
                for family, M, weights in (
                    ('validation-h',M_h,None),
                    ('GT19-h',M_h,M_h+RA.FLOOR*max(M_h.sum(),1e-300)*td.h),
                    ('GT19-EB',M_eb,M_eb+RA.FLOOR*max(M_eb.sum(),1e-300)*td.h)):
                    # Exactly reproduce the frozen no-repeat snap for proportional h.
                    if weights is not None and weights.sum()>0 and np.allclose(weights/weights.sum(),td.h,rtol=1e-12,atol=0):
                        weights = td.v+1.
                    t = time.perf_counter(); c = E5.build(setup,scores,tree,kib,0.,weights=weights)
                    static_build_s += time.perf_counter()-t
                    t = time.perf_counter(); rec = region_record(c,td,M,family,eb if family=='GT19-EB' else None)
                    rows.append(rec); built.append(c);static_analysis_s += time.perf_counter()-t
            phase.update(static_tree_prepare_s=tree_prepare_s,EB_fit_s=alpha_s,mass_construction_s=mass_s,
                         all_static_build_s=static_build_s,all_static_analysis_s=static_analysis_s)
            assert built, 'No feasible predefined static learned candidate'
            # Every zero-tree cache fraction is explicit; predictive choice never sees replay.
            t = time.perf_counter()
            zeros = [Z.build_row(setup,scores,kib,r) for r in zero_rows]
            phase['zero13_build_s'] = time.perf_counter()-t
            zpred = min(range(13),key=lambda i:(zero_rows[i]['pred'],zero_rows[i]['frac']))
            eb_candidates = [(rows[i]['A_B_available_budget']['capped_FP'],c['trees'],c['frac'],'static',i)
                             for i,c in enumerate(built) if rows[i]['family']=='GT19-EB']
            hchoices = eb_candidates+[(r['pred'],0,r['frac'],'zero',i) for i,r in enumerate(zero_rows)]
            heuristic = min(hchoices)
            hmeta = dict(enabled=ticket['heuristic'],name='KL-EB22-static13',
                         predicted_objective=heuristic[0],trees=heuristic[1],frac=heuristic[2],
                         family=heuristic[3],index=heuristic[4],
                         guarantee='none; capped conditional proxy, not deployed CLOCK optimality') if ticket['heuristic'] else None
            # Exact learning replay is reference-only, AFTER predictive choices are fixed.
            t = time.perf_counter(); zb, replay_rows = E5.replay_best(zeros,learn,setup,safe)
            phase['BF13_reference_learning_replay_s'] = time.perf_counter()-t
            zexact = next(i for i,c in enumerate(zeros) if c is zb)
            refs = {}
            t = time.perf_counter(); old_c,old_info = RA6.select6(setup,scores,lm_old,kib,H)
            phase['RA6_frozen_selection_build_s'] = time.perf_counter()-t
            refs['RA6-frozen'] = (old_c,old_info,lm_old)
            t = time.perf_counter()
            if same_stats:
                new_c,new_info = old_c,dict(old_info)
                phase['RA6_GT19_reused_identical_stats'] = True
            else:
                with patched():
                    new_c,new_info = RA6.select6(setup,scores,lm,kib,H)
                phase['RA6_GT19_reused_identical_stats'] = False
            phase['RA6_GT19_incremental_selection_build_s'] = time.perf_counter()-t
            refs['RA6-GT19'] = (new_c,new_info,lm)
            # Export selected RA6 structure with honest candidate-dependent T labelling.
            ref_records = {}
            for refname,(c,info,stats) in refs.items():
                td = E5.tree(setup,scores,c['trees'])
                P = RA.population(stats,td,H,RA.Config(new_mix=0.))
                Meff = P.misses(c['structure'].seg_fpr_cont,c['slots'],True)
                rec = region_record(c,td,Meff,refname,external_T=0. if c['cache_bytes']==0 else None)
                if refname == 'RA6-frozen':
                    rec['miss_source'] = 'original frozen GT statistics; post-build population proxy'
                rec['selection_info'] = info
                ref_records[refname] = rec
            selection_envelope_s = time.perf_counter()-selection_start
            # This boundary is deliberate: first access to evaluation counts/results.
            eval_start = time.perf_counter()
            tail_freq = np.bincount(tail,minlength=len(setup.h1q))
            for rec,c in zip(rows,built):
                st=c['structure'];nr=len(st.f)
                actualM=np.bincount(st.q_region,weights=tail_freq,minlength=nr)
                actualFP=np.bincount(st.q_region,weights=tail_freq*st.fp_static,minlength=nr)
                rec['actual_tail_FP']=int(actualFP.sum())
                rec['actual_tail_M_T0']=actualM.tolist()
                rec['actual_tail_FP_by_region']=actualFP.astype(int).tolist()
                rec['posthoc_true_tail_A_B']=theory_layers(rec['n'],actualM,rec['q'],rec['bloom_available_bits'],plain_bits)
                rec['posthoc_tail_note']='Evaluation-only diagnosis, never used for EB, candidate ranking or selection'
            selected = {'BF-no-cache':zeros[0], 'BF13-Predict-GT19':zeros[zpred],
                        'BF13-ExactLearning':zeros[zexact],
                        **{k:v[0] for k,v in refs.items()}}
            if hmeta:
                selected[hmeta['name']] = built[heuristic[4]] if heuristic[3]=='static' else zeros[heuristic[4]]
            methods={}; memo={}
            for method,c in selected.items():
                ident=identity(c); key=(ident['static_flags_sha256'],c['cache_bytes'])
                if key not in memo:
                    result=E5.evaluate(c,tail,setup,safe)
                    memo[key]=dict(fp=int(result['fp']),hits=int(result['hits']))
                methods[method]=dict(identity=ident,tail=memo[key],
                    evaluation_reuse_key=list(key),member_zero_FN_asserted_at_build=True)
                if method in ref_records:
                    ref_records[method]['actual_tail_FP']=memo[key]['fp']
            zero_records=[]
            rates,multiplicity=np.unique(lm.rate,return_counts=True)
            P0=RA.ra4.Population(np.zeros(len(rates),np.int64),rates,multiplicity.astype(float),
                np.array([H*lm.N1/lm.L]),np.array([len(setup.h1m)],float),np.ones(1),H)
            for i,(c,r) in enumerate(zip(zeros,zero_rows)):
                fp,cutoff=replay_rows[(0,c['frac'])]
                st=c['structure']
                zero_M=P0.misses(np.array([st.est_fpr]),c['slots'],True)
                assert np.isclose(float(zero_M[0]*st.est_fpr),r['pred'],rtol=1e-10,atol=1e-10)
                zero_records.append(dict(identity=identity(c),bf_bits=r['bf_bits'],bf_k=r['bf_k'],
                    p=[1.],q=[1.],n=[len(setup.h1m)],M=zero_M.tolist(),W=float(zero_M.sum()),
                    r=[1.] if zero_M.sum()>0 else None,model_bytes=0,
                    miss_source='frozen one-region GT19/Che population, directly recomputed, not inferred from measured FP',
                    bloom_logical_bits=r['bf_bits'],bloom_array_bits=r['bf_bits'],
                    m=[r['bf_bits']],k=[r['bf_k']],kind=[int(E5.C.BF)],
                    epsilon_continuous_ideal=[float(np.exp(-A*r['bf_bits']/len(setup.h1m)))],
                    budget_bytes=kib*1024,unused_bytes=kib*1024-int(st.used_bytes),
                    metadata_bytes=int(st.metadata_bytes),array_overhead_bytes=int(st.array_overhead_bytes),
                    cache_slots=c['slots'],epsilon_integer_ideal=float(st.est_fpr),
                    predicted_FP=float(r['pred']),learning_FP_or_cutoff=int(fp),learning_cutoff=bool(cutoff),
                    predictive_winner=i==zpred,exact_learning_winner=i==zexact,
                    T=0. if not c['cache_bytes'] else None,
                    T_note='external T=0' if not c['cache_bytes'] else 'candidate-dependent Che mixture, not shared with learned candidates'))
            row=dict(case_index=ci,**case,seed=cfg['seed'],cache='index',learn_len=len(learn),tail_len=H,
                stream_sha256=hashlib.sha256(memoryview(stream).cast('B')).hexdigest(),
                old_GT19_rate_identical=same_stats,total_rate_seen_plus_unseen=float(lm.rate.sum()+lm.N1/lm.L),
                EB_fits=fits,static_candidates=rows,skipped_static=skipped,zero13=zero_records,
                references=ref_records,methods=methods,heuristic=hmeta,phase_seconds=phase,
                stream_prepare_s=stream_s,selection_pipeline_envelope_s=selection_envelope_s,
                timing_note='Single diagnostic pass, not a benchmark. Envelope charges all alpha/proxy/build/ref work; conservative heuristic cost, not a fair standalone selection comparison. Training absent; shared input prepare reported separately.',
                evaluation_s=time.perf_counter()-eval_start)
            out['cases'].append(row);save(output,out)
            print('CASE COMPLETE',ci,{k:v['tail']['fp'] for k,v in methods.items()},flush=True)
            del stream,learn,tail,tail_freq,built,zeros,refs,selected,memo,rows,lm,lm_old
        verify_freeze()
        out['status']='complete'
    except Exception:
        out['status']='error';out['error']=traceback.format_exc()
        print(out['error'],flush=True)
    out['whole_worker_s']=time.perf_counter()-start
    save(output,out)
    if out['status']!='complete':
        raise SystemExit(1)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',required=True)
    p.add_argument('--ticket',required=True)
    p.add_argument('--output',required=True)
    main(p.parse_args())
