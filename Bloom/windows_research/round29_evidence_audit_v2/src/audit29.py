"""Fixed dataset-cluster analysis and physical-resource/collision audit."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
for r in ('round5_dp','round10_fpcache','round17_zerotree','round19_gt_fix','round20_zero_guard'):sys.path.insert(0,str(WR/r/'src'))
import engine5 as E5
import cache_fp
import report17
import report19
import report20
import numpy as np
from scipy import stats
import csv
import hashlib
import json
from collections import defaultdict


def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def readcsv(p):
    with p.open() as f:return list(csv.DictReader(f))
def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True);q=p.with_suffix(p.suffix+'.tmp');q.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');q.replace(p)
def writecsv(p,rows):
    with p.open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def group(w):
    if w=='真实轨迹':return '真实轨迹'
    for x in ('1万','10万','100万','全部'):
        if w.endswith('-'+x):return x+' key 池'
    return '每key一次/全新对抗'


def clustered(rows,column):
    cl=defaultdict(list)
    for r in rows:cl[r['dataset'],group(r['workload'])].append(np.log((int(r[column])+1)/(int(r['replay_fp'])+1)))
    means={k:float(np.mean(v)) for k,v in cl.items()};ds=sorted({k[0] for k in means})
    assert len(means)==21 and len(ds)==8
    sums=np.array([sum(v for (d,g),v in means.items() if d==name) for name in ds]);counts=np.array([sum(d==name for d,g in means) for name in ds])
    points=sums/counts;idx=np.random.default_rng(2901).integers(0,len(ds),(50000,len(ds)))
    boot=sums[idx].sum(1)/counts[idx].sum(1);equal=points[idx].mean(1)
    se=points.std(ddof=1)/np.sqrt(len(ds));margin=stats.t.ppf(.975,len(ds)-1)*se
    nonzero=np.array([v for v in means.values() if v!=0])
    return dict(original_cluster_count=len(means),datasets=len(ds),original_equal_cluster_ratio=float(np.exp(sums.sum()/counts.sum())),
                original_cluster_wilcoxon_two_sided=float(stats.wilcoxon(nonzero,alternative='two-sided').pvalue),
                original_cluster_wins=sum(v<0 for v in means.values()),original_cluster_losses=sum(v>0 for v in means.values()),
                dataset_cluster_percentile95=np.exp(np.quantile(boot,[.025,.975])).tolist(),
                equal_dataset_ratio=float(np.exp(points.mean())),equal_dataset_percentile95=np.exp(np.quantile(equal,[.025,.975])).tolist(),
                equal_dataset_t95=np.exp([points.mean()-margin,points.mean()+margin]).tolist(),
                per_dataset=[dict(dataset=d,clusters=int(c),paired_geometric_ratio=float(np.exp(v))) for d,c,v in zip(ds,counts,points)],
                cluster_rows=[dict(dataset=d,group=g,log_ratio=v,cases=len(cl[d,g])) for (d,g),v in means.items()])


def collision_check():
    # Two distinct semantic keys represented by the same64-bit hash, injected deliberately.
    h=np.array([0x1234567890abcdef],np.uint64);safe=E5.E.CC.safe_prefix_lengths(h,h)
    p=E5.K.layout(2048);data=E5.K.allocate(p)
    outcome=E5.K.insert(data,h[0],int(safe[0]),p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4,p['handbits'])
    hit=E5.K.lookup(data,h[0],p['buckets'],40,p['Q'],p['ob'],p['slot_bits'],4)
    assert outcome==0 and not hit
    f=cache_fp.layout(2048);data=cache_fp.allocate(f)
    outcome_f=cache_fp.insert(data,h[0],f['buckets'],64,f['Q'],f['ob'],f['slot_bits'],4,f['handbits'])
    hit_f=cache_fp.lookup(data,h[0],f['buckets'],64,f['Q'],f['ob'],f['slot_bits'],4)
    assert outcome_f==1 and hit_f
    return dict(injected_representational_collision=True,real_collision_discovered=False,safe_length=int(safe[0]),prefix_insert_bypassed=True,prefix_member_rejected=False,fp64_member_rejected=True)


def resources():
    rows=[]
    import lightgbm as lgb
    from end_to_end import model_arrays
    models={}
    for cache,directory,method in (('index',WR/'round6_bucket/results/main','RA6'),('fp64',WR/'round10_fpcache/results/main','RA6-fp64')):
        for f in sorted(directory.glob('rows_*.csv')):
            candidates=[r for r in readcsv(f) if r['method']==method and int(r['seed'])==0 and r['workload'] in ('真实轨迹','uniform-1万')]
            assert len(candidates)==1,(f,len(candidates));r=candidates[0];ds=r['dataset']
            with np.load(E5.C.CACHE/ds/'data.npz',allow_pickle=False) as z:n=int(z['y'].sum())
            modelpath=E5.C.CACHE/ds/'model200.txt'
            if ds not in models:models[ds]=lgb.Booster(model_file=str(modelpath))
            arrays=model_arrays(models[ds],int(r['trees']));k=E5.D.K_REG
            known=dict(model_bytes=sum(a.nbytes for a in arrays.values()),metadata_bytes=(k+1)*8+k*(1+8+8)+(k+1)*8,
                       overhead_bytes=12*sys.getsizeof(np.empty(0,np.uint8))+sys.getsizeof(arrays))
            if cache=='index':
                fields={k:int(r[k]) for k in ('model_bytes','bf_bytes','metadata_bytes','overhead_bytes','cache_alloc_bytes','total_bytes')}
                assert all(fields[k]==v for k,v in known.items())
                breakdown_source='archived component fields; model/layout independently checked'
            else:
                fields=dict(**known,cache_alloc_bytes=int(r['cache_alloc_bytes']),total_bytes=int(r['total_bytes']))
                fields['bf_bytes']=fields['total_bytes']-sum(known.values())-fields['cache_alloc_bytes']
                breakdown_source='model/layout reconstructed; BF payload derived from archived total minus known components; NOT fresh BF build'
            assert fields['bf_bytes']>=0
            assert sum(fields[k] for k in fields if k!='total_bytes')==fields['total_bytes']<=int(r['budget_kib'])*1024
            slots=(E5.K if cache=='index' else cache_fp).layout(fields['cache_alloc_bytes'])['slots']
            payload=8*n if cache=='index' else 0;header=sys.getsizeof(np.empty(0,np.uint64)) if cache=='index' else 0
            rows.append(dict(dataset=ds,budget_kib=int(r['budget_kib']),cache=cache,workload=r['workload'],trees=int(r['trees']),members=n,breakdown_source=breakdown_source,model_source_sha256=sha(modelpath),**fields,
                             backend_verification_index_payload_bytes=payload,backend_verification_index_header_bytes=header,
                             deployment_plus_verification_index_bytes=fields['total_bytes']+payload+header,
                             index_payload_to_filter_budget=payload/(int(r['budget_kib'])*1024),cache_capacity_slots=slots,
                             ideal_hash_per_member_query_collision_bound=min(1.,slots/2**64) if cache=='fp64' else 0.,source=str(f.relative_to(BLOOM)),source_sha256=sha(f)))
    assert len(rows)==60
    return rows


def freeze():
    p=ROOT/'plan/freeze.json';assert not p.exists()
    files={Path(__file__),ROOT/'plan/design-freeze.md',WR/'round19_gt_fix/results/updated_main_comparisons.csv'}
    for directory in ('round6_bucket/results/main','round10_fpcache/results/main'):files.update((WR/directory).glob('rows_*.csv'))
    for directory in ('round17_zerotree','round19_gt_fix','round20_zero_guard'):
        files.update((WR/directory/'src').glob('*.py'));files.add(WR/directory/'plan/freeze.json');files.add(WR/directory/('results/main/completion.json' if directory=='round17_zerotree' else 'results/completion.json'))
    save(p,dict(date='2026-11-21',paper_version='e256658:vldb',sources_and_inputs={str(q.relative_to(BLOOM)):sha(q) for q in sorted(files)}))


def run():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in manifest['sources_and_inputs'].items():assert sha(BLOOM/p)==h,p
    out=ROOT/'results';out.mkdir(exist_ok=True);assert not (out/'summary.json').exists()
    report19.collect();report17.collect();gate=report20.collect()
    base=readcsv(WR/'round19_gt_fix/results/updated_main_comparisons.csv');summary={}
    for mode in ('index','fp64'):
        rr=[r for r in base if r['cache']==mode and r['cohort']=='main' and r['included']=='True' and r['workload']!='探测重放10%'];assert len(rr)==748
        for column in ('old_ra_fp','repaired_ra_fp'):summary[f'{mode}/{column}']=clustered(rr,column)
    resource=resources();writecsv(out/'resources.csv',resource);collision=collision_check()
    gate_rows=gate[0];zero=dict(cases=len(gate_rows),zero_selected=sum(r['gate']['family']=='zero' for r in gate_rows),
                            tail_regressions_vs_BF=sum(r['methods']['RA6-ZGate']['fp']>r['methods']['BF+ReplayCache']['fp'] for r in gate_rows),
                            tail_regressions_vs_RA6=sum(r['methods']['RA6-ZGate']['fp']>r['methods']['RA6-GT19']['fp'] for r in gate_rows),cohorts=gate[2])
    save(out/'summary.json',dict(statistics=summary,collision_test=collision,zero_tree=zero,resource_rows=len(resource),freeze_sha256=sha(ROOT/'plan/freeze.json')))
    text=['# Dataset-cluster uncertainty and system assumptions','',
          'Analysis only. Original inclusion/cohorts/grouping retained. New uncertainty resamples whole datasets, not748dependent cases. Only8dataset clusters: intervals are sensitivity estimates, not a population-wide or equivalence guarantee.','',
          '| Cache | Counts | Original21-cluster effect | Dataset-cluster95%CI | Historical cluster p(two-sided) | Equal-dataset effect (sensitivity) |',
          '|---|---|---:|---|---:|---:|']
    for key,d in summary.items():
        mode,count=key.split('/');lo,hi=d['dataset_cluster_percentile95']
        text.append(f'| {mode} | {count} | {d["original_equal_cluster_ratio"]:.6f} | [{lo:.6f},{hi:.6f}] | {d["original_cluster_wilcoxon_two_sided"]:.6f} | {d["equal_dataset_ratio"]:.6f} |')
    text+=['','## Dataset effects (descriptive, repaired counts)','', '| Cache | Dataset | Workload groups | Geometric paired RA/Replay |','|---|---|---:|---:|']
    dsrows=[]
    for mode in ('index','fp64'):
        for r in summary[f'{mode}/repaired_ra_fp']['per_dataset']:
            dsrows.append(dict(cache=mode,**r));text.append(f'| {mode} | {r["dataset"]} | {r["clusters"]} | {r["paired_geometric_ratio"]:.6f} |')
    writecsv(out/'dataset_effects.csv',dsrows)
    text+=['','## Interpretation','',
           '- No repeated regrouping to obtain p<.05. The historical21-cluster test is reproduced, not promoted to a dataset-independent test. The new primary interval keeps its original effect weighting but clusters resampling at dataset level.',
           '- “Similar observed FP counts at lower selection cost” is supported as a descriptive engineering tradeoff; “statistically equivalent”, “universally better”, and “significantly lower FP” do not follow.',
           '- Selection efficiency is a separate contribution: round15 measures learning-length scaling to100M with fixed candidate grid. It is not an asymptotic class separation at fixed candidate count. Old statistic-only timing cannot be transferred to the replay-based zero guard.',
           '', '## Memory and guarantees','',
           'resources.csv contains60historical actual selected configurations, including complete filter byte totals and the external member-index cost. All60 totals are checked. The selected representative cases are unaffected by the GT gap repair. They are not new deployment executions.',
           '', '| Component | Verified-prefix index supplied by backend | Index-free fp64 |','|---|---|---|',
           '| Executable model, BF bits, thresholds/navigation, array headers | Inside filter budget | Inside filter budget |',
           '| Packed CLOCK array including header and empty slots | Inside filter budget | Inside filter budget |',
           '| Sorted member-hash verification index | Backend8*n bytes + owning-array header | Not required for cache verification |',
           '| Backend records/exact keys | Backend, not measured as zero | Backend, not measured as zero |',
           '| Training, scoring, learning counters, candidate scratch | Construction/selection workspace, not deployed-filter budget | Same distinction |',
           '', '- If the backend does NOT already provide the index, index construction, storage and safe-prefix search are extra work; the verified-prefix design is not automatically native to RocksDB/LSM backends.',
           '- Prefix safety requires definitive negative feedback, a complete static member-hash index and bypass when no safe prefix fits. Member/model/router updates require rebuild/invalidation; checking today’s members is not a dynamic-set proof.',
           '- fp64 has probabilistic false negatives: under ideal non-adversarial hashing, at most min(1,S/2^64) per member query for S resident entries. This is not a universal lifetime, adversarial, or fixed2.4e-15 guarantee. Collision injection confirms an fp64 rejection while the safe-prefix format bypasses the same hash alias.',
           '', '## Zero-tree is already experimentally covered','',
           f'- Revalidated round17 predictive variant and round20 exact-learning guard. Guard:{zero["cases"]}cases,{zero["zero_selected"]}zero-tree choices,{zero["tail_regressions_vs_BF"]}tail regressions versus BF+Cache,{zero["tail_regressions_vs_RA6"]}versus repaired RA6.',
           '- All32TCP-only cases choose BF; all80strong-model controls keep RA6. These are outcomes of the frozen learning rule, not guarantees on future traffic. All80fresh controls choose BF, changing the original no-repeat/Gama reduction.',
           '- Predictive RA6-Z is cheaper but does not always select BF on weak TCP and retains losses; ZGate pays for13BF candidates plus a learned-finalist learning replay. Neither silently replaces original RA6.',
           '- Cancelled round21 stays cancelled;735/2880partial timings do not constitute a completed cost comparison.']
    (out/'report.md').write_text('\n'.join(text)+'\n')
    print(json.dumps(dict(statistics={k:{x:v[x] for x in ('original_equal_cluster_ratio','dataset_cluster_percentile95','original_cluster_wilcoxon_two_sided')} for k,v in summary.items()},zero_tree={k:v for k,v in zero.items() if k!='cohorts'},collision=collision,resource_rows=len(resource)),indent=2),flush=True)
    save(out/'completion.json',dict(status='complete',source_rows=len(base),eligible_per_cache=748,resource_rows=60,bootstrap_replicates=50000,seed=2901))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();freeze() if a.freeze else run()
