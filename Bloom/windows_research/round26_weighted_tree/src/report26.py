"""Standard-library verification/report of the complete weighted-LightGBM trial."""
import argparse
import json
import hashlib
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
DATASETS=('url','caida_tcp_flow','caida')
ARMS=('Uniform','TrafficGT','EscapeGT')
TREES=(1,4,8,16,48,160)


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def make():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    done=json.loads((ROOT/'results/completion.json').read_text())
    assert done['status']=='complete' and done['configurations']==108 and done['freeze_sha256']==digest(ROOT/'plan/freeze.json')
    for rel,want in freeze['sources'].items():assert digest(BLOOM/rel)==want,rel
    lines=['# Proposal A: fixed LightGBM, only negative training weights change','',
           'Three datasets, three weighting arms, six tree prefixes, cache fractions0/10%. '
           'One fixed model/workload seed. All108 planned configurations are retained, including12 that cannot fit. '
           'TrafficGT is a query-mass control; EscapeGT transfers a fixed reference\'s cache-residual proxy through32 score bins, not oracle future key-level misses.','']
    comparisons=[];valid=infeasible=0
    for ds in DATASETS:
        r=json.loads((ROOT/f'results/main/{ds}.json').read_text())
        assert r['status']=='complete' and r['exit_code']==0 and r['dataset']==ds
        assert r['openblas_threads']==r['numba_threads']==1
        assert len(r['results'])==36
        by={(v['arm'],v['trees'],v['frac']):v for v in r['results']}
        assert set(by)=={(a,t,f) for a in ARMS for t in TREES for f in (0.,.1)}
        info=r['training_negative_weight_map']
        assert len(info['cuts'])==31 and len(info['escape_mass'])==32
        assert all(0<=a<=b+1e-8*max(1,b) for a,b in zip(info['escape_mass'],info['traffic_mass']))
        for k in ('traffic_transfer','escape_transfer'):
            assert math.isclose(info[k]['mean_negative_weight'],1.,rel_tol=1e-12)
            assert info[k]['negative_weight_min']>0 and 0<info[k]['supported_target_mass']<=1+1e-12
        lines += [f'## {ds}: {r["budget_kib"]}KiB','',
                  f"Weighted-arm reference acquisition: {r['reference_train_s']+r['reference_prepare_s']:.3f}s (reference training + scoring/build/mapping).",
                  '', '| Trees | Cache fraction | Uniform FP | TrafficGT FP | EscapeGT FP | Uniform score ns | Traffic score ns | Escape score ns |',
                  '|---:|---:|---:|---:|---:|---:|---:|---:|']
        for f in (0.,.1):
            for t in TREES:
                rr=[by[a,t,f] for a in ARMS]
                if any(v['status']=='infeasible' for v in rr):
                    assert all(v['status']=='infeasible' for v in rr)
                    infeasible+=3;lines.append(f'| {t} | {f} | infeasible | infeasible | infeasible | — | — | — |');continue
                valid+=3
                for v in rr:
                    assert v['status']=='ok' and v['member_fn']==0 and v['native_pool_flags_equal']
                    assert v['total_bytes']<=r['budget_kib']*1024 and 0<=v['tail_fp']<=r['tail_queries']
                    assert math.isclose(v['tail_fpr'],v['tail_fp']/r['tail_queries'],rel_tol=1e-12)
                    for k in ('native_model','native_full'):
                        assert len(v[k+'_ns_all'])==3 and min(v[k+'_ns_all'])>0
                        assert median(v[k+'_ns_all'])==v[k+'_ns_median']
                lines.append(f'| {t} | {f} | '+' | '.join(str(v['tail_fp']) for v in rr)+' | '+' | '.join(f"{v['native_model_ns_median']:.1f}" for v in rr)+' |')
                comparisons.append(dict(dataset=ds,trees=t,frac=f,uniform_fp=rr[0]['tail_fp'],traffic_fp=rr[1]['tail_fp'],escape_fp=rr[2]['tail_fp']))
    assert (valid,infeasible,len(comparisons))==(96,12,32)
    summary=dict(planned=108,feasible=valid,infeasible=infeasible,matched_configurations=len(comparisons))
    for ref,field in (('Uniform','uniform_fp'),('TrafficGT','traffic_fp')):
        summary['EscapeGT_vs_'+ref]=dict(wins=sum(r['escape_fp']<r[field] for r in comparisons),
          ties=sum(r['escape_fp']==r[field] for r in comparisons),losses=sum(r['escape_fp']>r[field] for r in comparisons),
          median_smoothed_ratio=median((r['escape_fp']+1)/(r[field]+1) for r in comparisons))
    lines+=['','## Boundaries','',
            '- EscapeGT versus Uniform has '+str(summary['EscapeGT_vs_Uniform']['wins'])+' wins, '+str(summary['EscapeGT_vs_Uniform']['ties'])+' ties and '+str(summary['EscapeGT_vs_Uniform']['losses'])+' losses across32 feasible matched configurations. This is mixed exploratory evidence, not a stable general advantage.',
            '- No demonstration that a few weighted trees replace160 unweighted trees on the intended full-budget tradeoff. Tree-prefix results and infeasibility are preserved rather than selecting a favorable winner after testing.',
            '- All arms use identical LightGBM settings and training-key identities. Negative weights are mean-normalized to1, positives stay1. A fixed reference16-tree/10%-cache predictor transfers coarse-bin learning mass to disjoint training negatives; this is not true per-training-key future m_x or joint model/cache training.',
            '- TrafficGT separates adaptation to query distribution from cache-specific absorption. Reference assumptions can become inaccurate when final model/cache configuration changes; weights are not recomputed to fix observed failures.',
            '- Three native-loop timing repetitions use known labels for simulated feedback, not a real database. Input hashes and features are prepared; standalone scoring and full model/BF/cache costs are distinct. There is only one model/workload seed; no significance or paired cross-campaign speedup claim.',
            '- Weighted arms incur extra reference training/scoring/mapping cost. Full tree model is trained once per arm, prefixes reused. The application does not automatically choose a prefix from test outcomes.',
            '- All feasible member/pool-native checks passed. Old frozen methods, cancelled experiments, dependency environments and paper files remain unchanged.']
    return {'report.md':'\n'.join(lines)+'\n','summary.json':json.dumps(summary,indent=2)+'\n','paired_configurations.json':json.dumps(comparisons,indent=2)+'\n'}


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');a=parser.parse_args()
    for name,text in make().items():
        p=ROOT/'results'/name
        if a.verify_only:assert p.read_bytes()==text.encode(),name
        else:p.write_bytes(text.encode())
    print('PASS:108 planned configurations,96 feasible,12 infeasible; all matched FP/byte/timing checks')
