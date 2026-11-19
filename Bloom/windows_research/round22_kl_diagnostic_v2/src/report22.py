"""Offline verification and report; no training, data loading or candidate retuning."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1]
A=math.log(2)**2
HEURISTIC='KL-EB22-static13'


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def close(x,y):
    assert math.isfinite(x) and math.isfinite(y)
    assert math.isclose(x,y,rel_tol=2e-8,abs_tol=1e-8),(x,y)


def continuous(n,M,bits):
    """Independent bisection in log water level, honoring PASS/EMPTY and budget."""
    assert bits>=0 and sum(n)>0
    active=[i for i in range(len(n)) if n[i]>0 and M[i]>0]
    out=[1. if x>0 else 0. for x in n]
    if bits==0 or not active:return out
    z={i:math.log(M[i]/n[i]) for i in active}
    low=min(z.values())-bits*A/sum(n[i] for i in active)-2
    high=max(z.values())+1
    for _ in range(160):
        mid=(low+high)/2
        used=sum(n[i]*max(0,z[i]-mid) for i in active)/A
        if used>bits:low=mid
        else:high=mid
    for i in active:out[i]=math.exp(-max(0,z[i]-high))
    close(sum(-n[i]*math.log(out[i])/A for i in active),bits)
    return out


def check_theory(t):
    n,M,q=t['n'],t['M'],t.get('B',{}).get('q') if t.get('B') else None
    e=continuous(n,M,t['bits']);fp=sum(x*y for x,y in zip(M,e));close(fp,t['capped_FP'])
    close(sum(M),t['W']);close(t['beta'],A*t['bits']/sum(n))
    for x,y in zip(e,t['capped_epsilon']):close(x,y)
    if not t['W']:return
    p=[x/sum(n) for x in n];r=[x/t['W'] for x in M]
    if all(y>0 for x,y in zip(p,r) if x>0):
        D=sum(x*math.log(x/y) for x,y in zip(p,r) if x>0)
        close(D,t['KL']);rel=t['W']*math.exp(-t['beta']-D);close(rel,t['relaxed_FP'])
        assert rel<=fp+1e-8*max(1,fp)
        if t['interior_legal']:close(rel,fp)
    if q is not None:
        eq=continuous(n,q,t['bits']);cost=sum(x*y for x,y in zip(M,eq))
        if fp>0:close(cost/fp,t['B']['capped_loss_ratio'])
        if t['B']['interior_equality_applicable']:close(t['B']['capped_loss_ratio'],t['B']['arithmetic_geometric_factor'])
    if 'plain_bits' in t:
        plain=t['W']*math.exp(-A*t['plain_bits']/sum(n))
        close(plain,t['same_W_plain_proxy']);close(fp/plain,t['same_W_capped_ratio'])
        assert t['capped_same_W_says_win']==(fp<plain) or math.isclose(fp,plain,rel_tol=1e-10)


def compare(rows,ref):
    pairs=[(c['methods'][HEURISTIC]['tail']['fp'],c['methods'][ref]['tail']['fp']) for c in rows]
    return dict(cases=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),
                losses=sum(a>b for a,b in pairs),median_smoothed_ratio=median((a+1)/(b+1) for a,b in pairs))


def collect(root=ROOT,with_inputs=False):
    bloom=root.parents[1];wr=root.parent;files={}
    def read(p):
        files[str(p.relative_to(bloom))]=digest(p)
        return json.loads(p.read_text())
    freeze=read(root/'plan/freeze.json');cfg=read(root/'plan/protocol.json')
    # Explicit, exact-hash exception for a nonexecuted report changed by the user.
    # Never restore old publication prose merely to satisfy an overbroad freeze.
    compatibility=read(root/'plan/publication-compatibility.json')
    variants=compatibility['allowed_nonruntime_report_variants']
    assert set(variants)=={'windows_research/round17_zerotree/src/report17.py'}
    source_variants=[]
    for rel,h in freeze['source_sha256'].items():
        actual=digest(bloom/rel)
        if actual!=h:
            v=variants.get(rel)
            assert v and v['experiment_sha256']==h and v['publication_sha256']==actual,rel
            source_variants.append(dict(path=rel,experiment_sha256=h,publication_sha256=actual,reason=v['reason']))
    completed=[];combined=[]
    for stage,expected in (('smoke',[0]),('matrix',list(range(1,13)))):
        done=read(root/f'results/{stage}/completion.json')
        assert done['status']=='complete' and done['heuristic']
        assert done['source_freeze_sha256']==digest(root/'plan/freeze.json')
        assert done['expected_new_cases']==done['new_cases']==len(expected)
        records=[]
        for rel,h in done['worker_sha256'].items():
            p=root/rel;assert digest(p)==h,rel
            w=read(p);assert w['status']=='complete' and w['heuristic_enabled']
            assert w['environment']['numba_threads']==1
            assert set(w['environment']['native_env'].values())=={'1'}
            if with_inputs:
                for src,want in w['inputs'].items():assert digest(bloom/src)==want,src
            log=p.with_suffix('.log');text=log.read_text();assert 'Traceback' not in text
            files[str(log.relative_to(bloom))]=digest(log)
            records+=w['cases']
        assert sorted(r['case_index'] for r in records)==expected
        if stage=='matrix':assert done['smoke_reference']['sha256']==digest(root/'results/smoke/completion.json') and done['total_cases_in_tables']==13
        combined+=records;completed.append(done)
    combined.sort(key=lambda c:c['case_index']);assert len(combined)==13
    rp=wr/'round13_complete/results/combined_baseline_rows.csv'
    with rp.open() as f:
        archive={(x['dataset'],int(x['budget_kib']),x['workload'],int(x['seed'])):x for x in csv.DictReader(f) if x['cache']=='index'}
    files[str(rp.relative_to(bloom))]=digest(rp)
    static=[];shrink=[]
    for c in combined:
        spec=cfg['matrix'][c['case_index']]
        assert all(c[k]==v for k,v in spec.items()) and c['seed']==0 and c['cache']=='index'
        assert c['old_GT19_rate_identical']
        ref=archive[c['dataset'],c['budget_kib'],c['workload'],0]
        assert c['stream_sha256']==ref['base_stream_sha256'] and c['tail_len']==int(ref['tail_len'])
        for method,field in (('RA6-frozen','ra_fp'),('RA6-GT19','ra_fp'),('BF-no-cache','bf_fp'),('BF13-ExactLearning','bfcache_fp')):
            assert c['methods'][method]['tail']['fp']==int(ref[field]),(c['case_index'],method)
        assert len(c['zero13'])==13
        assert [z['identity']['frac'] for z in c['zero13']]==cfg['zero_cache_fractions']
        zp=min(range(13),key=lambda i:(c['zero13'][i]['predicted_FP'],c['zero13'][i]['identity']['frac']))
        assert c['zero13'][zp]['predictive_winner']
        best=[i for i,z in enumerate(c['zero13']) if z['exact_learning_winner']];assert len(best)==1
        assert not c['zero13'][best[0]]['learning_cutoff']
        assert c['methods']['BF13-Predict-GT19']['identity']==c['zero13'][zp]['identity']
        assert c['methods']['BF13-ExactLearning']['identity']==c['zero13'][best[0]]['identity']
        for z in c['zero13']:
            assert z['model_bytes']==0 and z['metadata_bytes']==32
            assert z['identity']['total_bytes']<=c['budget_kib']*1024
            close(sum(z['M']),z['W']);close(z['predicted_FP'],z['W']*z['epsilon_integer_ideal'])
        by={}
        for idx,s in enumerate(c['static_candidates']):
            assert s['identity']['frac']==0 and s['cache_bytes']==0 and s['T']==0
            assert len(s['n'])==5 and s['identity']['total_bytes']<=c['budget_kib']*1024
            assert s['total_bytes']==s['model_bytes']+s['metadata_bytes']+s['array_overhead_bytes']+s['bloom_array_bits']//8
            assert s['bloom_logical_bits']==sum(s['m'])<=s['bloom_available_bits']
            close(sum(s['p']),1);close(sum(s['p_DP_smoothed']),1);close(sum(s['q']),1)
            close(sum(s['M']),s['W']);assert len(s['r'])==5
            for x,y in zip(s['M'],s['r']):close(y,x/s['W'])
            expected_int=[0. if n==0 else 1. if m==0 else (-math.expm1(-k*n/m))**k for n,m,k in zip(s['n'],s['m'],s['k'])]
            for x,y in zip(expected_int,s['epsilon_integer_ideal']):close(x,y)
            close(sum(m*e for m,e in zip(s['M'],expected_int)),s['predicted_integer_FP'])
            assert s['actual_tail_FP']==sum(s['actual_tail_FP_by_region'])
            close(sum(s['actual_tail_M_T0']),c['tail_len'])
            for key in ('A_B_available_budget','A_B_logical_deployed_budget','posthoc_true_tail_A_B'):check_theory(s[key])
            th=s['A_B_available_budget'];B=th['B'];real=c['methods']['BF-no-cache']['tail']['fp']
            assert real>0
            static.append(dict(case_index=c['case_index'],dataset=c['dataset'],workload=c['workload'],family=s['family'],
                trees=s['identity']['trees'],interior_legal=th['interior_legal'],KL=th['KL'],
                raw_KL_win=th['raw_KL_says_win'],capped_win=th['capped_same_W_says_win'],
                relaxed_FP=th['relaxed_FP'],capped_FP=th['capped_FP'],integer_expected_FP=s['predicted_integer_FP'],actual_FP=s['actual_tail_FP'],
                predicted_capped_to_plain_ratio=th['same_W_capped_ratio'],actual_to_plain_ratio=s['actual_tail_FP']/real,
                B_AM_GM=B['arithmetic_geometric_factor'],B_capped_loss=B['capped_loss_ratio'],B_interior_legal=B['interior_equality_applicable'],
                interpretation_B='conditional continuous model; not separately deployed q/r filters'))
            by.setdefault(s['identity']['trees'],{})[s['family']]=s
        assert len(by)==len(c['EB_fits'])
        for tree,ss in by.items():
            assert set(ss)=={'validation-h','GT19-h','GT19-EB'}
            fit=c['EB_fits'][str(tree)]
            assert sum(fit['singletons'])==fit['N1']
            close(sum(fit['h']),1);close(sum(fit['posterior_mean']),1)
            if fit['alpha'] is not None and fit['N1']>0:
                for count,h,u in zip(fit['singletons'],fit['h'],fit['posterior_mean']):close(u,(count+fit['alpha']*h)/(fit['N1']+fit['alpha']))
            shrink.append(dict(case_index=c['case_index'],dataset=c['dataset'],workload=c['workload'],trees=tree,
                h_static_FP=ss['GT19-h']['actual_tail_FP'],EB_static_FP=ss['GT19-EB']['actual_tail_FP'],
                alpha=fit['alpha'],endpoint=fit['endpoint']))
        choices=[(s['A_B_available_budget']['capped_FP'],s['identity']['trees'],0.,'static',i)
                 for i,s in enumerate(c['static_candidates']) if s['family']=='GT19-EB']
        choices += [(z['predicted_FP'],0,z['identity']['frac'],'zero',i) for i,z in enumerate(c['zero13'])]
        best=min(choices);h=c['heuristic'];assert h['enabled'] and h['name']==HEURISTIC
        assert best==(h['predicted_objective'],h['trees'],h['frac'],h['family'],h['index'])
        chosen=c['static_candidates'][best[4]] if best[3]=='static' else c['zero13'][best[4]]
        assert c['methods'][HEURISTIC]['identity']==chosen['identity']
        if best[3]=='static':assert c['methods'][HEURISTIC]['tail']['fp']==chosen['actual_tail_FP']
        else:assert c['methods'][HEURISTIC]==c['methods']['BF13-Predict-GT19']
        for m in c['methods'].values():
            assert m['member_zero_FN_asserted_at_build'] and 0<=m['tail']['fp']<=c['tail_len']
        assert all(isinstance(v,bool) or (math.isfinite(v) and v>=0) for v in c['phase_seconds'].values())
    assert len(static)==141 and len(shrink)==47
    stats=dict(cases=13,static_candidates=len(static),zero_candidates=169,
               interior_A=sum(s['interior_legal'] for s in static),interior_B=sum(s['B_interior_legal'] for s in static),
               relaxed_vs_capped_gate_reversals=sum(s['raw_KL_win'] is True and s['capped_win'] is False for s in static),
               selected_zero=sum(c['heuristic']['trees']==0 for c in combined),
               heuristic_vs={ref:compare(combined,ref) for ref in ('RA6-GT19','BF13-ExactLearning','BF13-Predict-GT19')},
               EB_vs_same_tree_h=dict(candidates=47,wins=sum(r['EB_static_FP']<r['h_static_FP'] for r in shrink),
                   ties=sum(r['EB_static_FP']==r['h_static_FP'] for r in shrink),losses=sum(r['EB_static_FP']>r['h_static_FP'] for r in shrink)))
    return combined,static,shrink,stats,dict(status='verified',cases=13,checked_raw_inputs=with_inputs,nonruntime_publication_source_variants=source_variants,
           mathematical_check='independent capped-waterlevel bisection; ideal formula and budget checks',records=files)


def render(cases,static,shrink,stats):
    lines=['# KL / Dirichlet shrinkage / zero-tree: actual-data diagnostic', '',
           '**This is the restricted KL-EB22-static13 diagnostic, not a full cache-aware EB-RA6 implementation.** '
           'Four predefined static learned prefixes (1/16/48/96 where feasible) compete against all 13 BF/cache fractions using predicted objectives. '
           'No confidence-bound guarantee is implemented. Exact learning replay is a separately labeled baseline, not part of heuristic selection.', '',
           '| Dataset | Workload | Chosen trees | Cache fraction | Heuristic FP | RA6-GT19 FP | BF+learning-replay FP |',
           '|---|---|---:|---:|---:|---:|---:|']
    for c in cases:
        h=c['methods'][HEURISTIC];m=c['methods']
        lines.append(f"| {c['dataset']} | {c['workload']} | {h['identity']['trees']} | {h['identity']['frac']} | {h['tail']['fp']:,} | {m['RA6-GT19']['tail']['fp']:,} | {m['BF13-ExactLearning']['tail']['fp']:,} |")
    lines+=['','## Main observations','']
    for ref,s in stats['heuristic_vs'].items():lines.append(f"- Versus {ref}: {s['wins']} wins / {s['ties']} ties / {s['losses']} losses; median per-case +1-smoothed FP ratio {s['median_smoothed_ratio']:.6f}.")
    e=stats['EB_vs_same_tree_h']
    lines += [f"- Zero trees selected in {stats['selected_zero']}/13 cases (the four TCP-only settings).",
              f"- Among141 actual static candidates, the unclipped A identity is applicable in only {stats['interior_A']}; B's two-interior-solution condition holds in {stats['interior_B']}. There are {stats['relaxed_vs_capped_gate_reversals']} raw-KL-versus-capped gate reversals within the stored conditional model.",
              f"- Holding tree count and cache=0 fixed, EB versus GT19-h has {e['wins']} lower, {e['ties']} equal and {e['losses']} higher actual FP counts across47 pairs. Partition/allocation may change between the pair; this is a shrinkage-pipeline comparison, not a pure distribution estimate error.",
              '- All original RA6 and ordinary BF/BF-replay reference FP counts and stream hashes match the archived round13 records. Old/new GT statistics are identical on this matrix; reused RA6-GT19 results are explicitly labeled, not fabricated as fresh independent timings.',
              '- The learned search has no cache candidates and no160/200-tree prefixes. Therefore its losses on repeated negatives cannot establish that KL theory or a complete EB-RA6 cache-aware selector fails. Conversely, success at t=0 does not establish the proposed full no-replay algorithm or future non-regression.',
              '- CAIDA/Shalla fresh-adversarial cases remain worse than BF and RA6. Even after capped optimization, predicted selected costs are far below actual tail FP. Fitting singleton histograms is not sufficient evidence of unseen-tail predictability. No parameter is retuned after these observations.']
    lines+=['','## Theory scatter inputs and what they mean','',
            '- A scatter compares the capped fixed-T proxy ratio to same-W ideal plain BF with the actual deployed static-filter/plain-BF FP ratio. Differences can include miss-mass estimation, model mismatch, DP smoothing/merging, integer hash counts and ideal BF error—not just clipping. Pure BF with cache is NOT used as the denominator for this T=0 comparison.',
            '- B scatter compares the AM/GM expression with the independently recomputed capped continuous loss on the SAME partition, budget and M. It is a mathematical-model check, NOT a pair of separately deployed q/r filter measurements. In the joint interior region the identity holds; outside it the expression need not equal the capped loss.',
            '- All plotted point-level data are preserved in static_checks.csv; common models/streams make points correlated. No claim of significance or of new information-theoretic novelty is made.',
            '- Real final5-region counts are used, not the optimistic1000-microbin KL. Physical model/metadata/array overhead and available/logical bits are exported. Cached references are labeled with nonshared candidate-dependent T and are not treated as fixed-T identities.']
    lines+=['','## Timing and reproducibility boundaries','',
            '- This is one diagnostic pass, not repeated fair algorithm timing. Per-phase seconds include EB fitting, proxy diagnostics, builds and reference work. selection_pipeline_envelope_s includes extra diagnostics/reference selection and is NOT a standalone selector cost or new speedup result.',
            '- Test tails are accessed after alpha fitting and predictive selection. Posthoc true-tail A/B fields are diagnostic only; no tail controls alpha, candidate ranking or t=0 decisions. Actual FP counts use frozen static flags/cache simulation, not new end-to-end database timing.',
            '- URL/CAIDA/Shalla with three workloads and four TCP-only second budgets:13 non-holdout, indexed-cache, seed0 settings. The matrix is small and prespecified; stronger claims need further independent validation. No entire192-case or fp64 replication is claimed.',
            '- The all-singleton EB input is not forced back to h and did not yield alpha=infinity in these fits. Original RA6 no-repeat reduction does not transfer to this heuristic. EB is a grid-refined working model; no global-MLE guarantee or bootstrap interval is claimed.',
            '- Initial v1 smoke failed at JSON serialization of a NumPy boolean; v2 only converts supported scalar types while still rejecting nonfinite values. Math, worker, candidate matrix and parameters are byte-identical. Failed logs remain separate and no performance result from v1 is used.',
            '- The cancelled shared-replay campaign was not restarted. No paper or frozen experimental source file was edited.']
    result={'report.md':'\n'.join(lines)+'\n','summary.json':json.dumps(stats,indent=2)+'\n'}
    for name,rows in (('static_checks.csv',static),('same_tree_shrinkage.csv',shrink)):
        out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows);result[name]=out.getvalue()
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    data=collect(with_inputs=a.inputs)
    for name,text in render(*data[:4]).items():
        path=ROOT/'results'/name
        if a.verify_only:assert path.read_bytes()==text.encode(),name
        else:path.write_bytes(text.encode())
    if not a.verify_only:(ROOT/'results/verification.json').write_text(json.dumps(data[4],indent=2)+'\n')
    print(json.dumps(data[3],indent=2));print('PASS:13 cases; reference reproduction, choices, physical budgets and independent A/B checks')
    if data[4]['nonruntime_publication_source_variants']:
        print('Explicit non-runtime publication source differences:',json.dumps(data[4]['nonruntime_publication_source_variants'],ensure_ascii=False))
