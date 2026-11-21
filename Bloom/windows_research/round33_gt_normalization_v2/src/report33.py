"""Verify all normalized arms and retain every improvement/regression; stdlib only."""
from pathlib import Path
import json,csv,hashlib,math
from statistics import median
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
ARMS=('GT19','SeenNormalize','TotalNormalize')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def substantive(arm):
    keys=('fp','hits','inserts','evictions','bypasses','processed','cutoff','occupied','member_hits_final','cache_state_sha256','cache_physical_bytes','trees','frac','total_bytes','payload','same_configuration_as_GT19','same_payload_as_GT19','rank_positions_changed','top5_overlap')
    return dict(values={k:arm[k] for k in keys},info={k:arm['info'][k] for k in ('predicted_fp','ra4_rank','candidates','built','normalization','table')})


def main():
    manifest=json.loads((ROOT/'plan/freeze.json').read_text());done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['arm_records']==180
    for p,h in manifest['sources'].items():assert sha(BLOOM/p)==h,p
    with (WR/'round19_gt_fix/results/updated_main_comparisons.csv').open() as f:refs={(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['cache']):r for r in csv.DictReader(f)}
    rows=[];inputs={};prior_checks=0;allcases=[]
    for job in done['jobs']:
        stem=job['dataset']+'_'+job['cache'];path=ROOT/f'results/{stem}.json';d=json.loads(path.read_text());inputs[path.name]=sha(path);assert d['status']=='complete'
        assert d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        before=WR/f'round33_gt_normalization/results/{stem}.json'
        previous={}
        if before.exists():
            old=json.loads(before.read_text());previous={(c['budget_kib'],c['workload'],c['seed']):c for c in old['cases']}
        for c in d['cases']:
            key=(c['dataset'],c['budget_kib'],c['workload'],c['seed'],c['cache']);assert c['arms']['GT19']['fp']==int(refs[key]['repaired_ra_fp'])
            allcases.append(key)
            for arm in ARMS:
                r=c['arms'][arm];info=r['info'];norm=info['normalization']
                assert r['member_hits_final']==0 and r['payload']['member_fn']==0 and r['total_bytes']<=c['budget_kib']*1024
                assert r['processed']==c['tail_queries'] and r['cutoff']==0
                assert info['normalization_s']>=0 and info['selector_wall_s']>=0
                assert math.isclose(info['normalize_and_select_s'],info['normalization_s']+info['selector_wall_s'],rel_tol=1e-12)
                assert norm['L']==c['learning_queries']
                if arm!='GT19':
                    assert abs(norm['total_mass']-1)<1e-12 and info['predicted_fp']<=c['tail_queries']*(1+1e-9)
                    if c['cohort']=='no_repeat':assert r['same_payload_as_GT19'] and r['fp']==c['arms']['GT19']['fp']
                pk=(c['budget_kib'],c['workload'],c['seed'])
                if pk in previous:
                    assert substantive(r)==substantive(previous[pk]['arms'][arm]),(key,arm,'Timing-only repair altered non-timing output');prior_checks+=1
                oldr=c['arms']['GT19']
                rows.append(dict(dataset=c['dataset'],cache=c['cache'],budget_kib=c['budget_kib'],workload=c['workload'],seed=c['seed'],cohort=c['cohort'],arm=arm,
                                 fp=r['fp'],GT19_fp=oldr['fp'],ratio=(r['fp']+1)/(oldr['fp']+1),trees=r['trees'],cache_frac=r['frac'],total_bytes=r['total_bytes'],
                                 raw_mass=norm['raw_total_mass'],new_mass=norm['total_mass'],seen_mass=norm['seen_mass'],unseen_mass=norm['unseen_mass'],
                                 configuration_changed=not r['same_configuration_as_GT19'],payload_changed=not r['same_payload_as_GT19'],rank_positions_changed=r['rank_positions_changed'],top5_overlap=r['top5_overlap'],
                                 count_s=c['count_s'],normalization_s=info['normalization_s'],selector_s=info['selector_wall_s'],normalize_and_select_s=info['normalize_and_select_s'],
                                 ranking_serialization_s=info['rank_serialization_s'],payload_check_s=r['payload_check_s'],tail_and_member_check_s=r['evaluate_s']))
    expected={(c['dataset'],c['budget_kib'],c['workload'],c['seed'],mode) for c in manifest['cases'] for mode in ('index','fp64')}
    assert len(rows)==180 and len(allcases)==60 and set(allcases)==expected and prior_checks==129
    with (ROOT/'results/rows.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    summary=[]
    for mode in ('index','fp64'):
        for arm in ARMS[1:]:
            for cohort in ('all','GT-gap affected','real_trace','TCP_only','no_repeat'):
                rr=[r for r in rows if r['cache']==mode and r['arm']==arm and (cohort=='all' or r['cohort']==cohort)]
                summary.append(dict(cache=mode,arm=arm,cohort=cohort,cases=len(rr),wins=sum(r['fp']<r['GT19_fp'] for r in rr),ties=sum(r['fp']==r['GT19_fp'] for r in rr),losses=sum(r['fp']>r['GT19_fp'] for r in rr),
                                    median_ratio=median(r['ratio'] for r in rr),configuration_changes=sum(r['configuration_changed'] for r in rr),payload_changes=sum(r['payload_changed'] for r in rr),
                                    cases_with_rank_changes=sum(r['rank_positions_changed']>0 for r in rr),cases_with_top5_changes=sum(r['top5_overlap']<5 for r in rr)))
    raw=[r['raw_mass'] for r in rows if r['arm']=='GT19']
    text=['# GT normalization ablation — completed v2','',
          '30prespecified case keys ×2cache formats ×3estimators=180records. GT19controls reproduce all60archived same-format FP counts. Both normalized estimators satisfy total effective mass1, but are not SGT or claimed unbiased estimators. Original L,N1,andcounts retain their meanings.','',
          f'Raw GT19total mass range in this matrix:[{min(raw):.12g},{max(raw):.12g}]. Stage1 and bucket refinement both use the new unseen mass. All32normalized no-repeat controls retain the GT19structure byte for byte and its FP count; this is not a claim about unmodified RA6’s universal equivalence to Gama.','',
          '| Cache | Variant | Cohort | Cases | Win/tie/loss vsGT19 | Median paired ratio | Config changes | Payload changes | Rank-changed cases | Top5-changed cases |',
          '|---|---|---|---:|---|---:|---:|---:|---:|---:|']
    for s in summary:text.append(f'| {s["cache"]} | {s["arm"]} | {s["cohort"]} | {s["cases"]} | {s["wins"]}/{s["ties"]}/{s["losses"]} | {s["median_ratio"]:.6f} | {s["configuration_changes"]} | {s["payload_changes"]} | {s["cases_with_rank_changes"]} | {s["cases_with_top5_changes"]} |')
    text+=['','## Scope and timing','',
           '- All cases and losses retained, including zeroFP; ratios use+1smoothing. Cases share data/models and are not independent statistical samples. No post-hoc selection of a winning estimator or change to the main algorithm.',
           '- In this matrix no top5set changed, although some within-grid ranks, final configurations and BF payloads changed. Enforcing mass1 does not guarantee lower held-out FP. The ablation concerns this fixed matrix, not all1146main cases.',
           '- Raw masses here are all at least1. The14repaired gap cases and8no-repeat controls remain unchanged; the8real/TCP controls carry the observed effects. Overall median1 is dominated by invariant controls and must not be interpreted as showing normalization is universally irrelevant. Real under-mass cases are not covered by this matrix.',
           '- V1stopped with129/180saved records because normalization had no separate component timer. Its process walltime included the cost, but the promised breakdown was incomplete. V2only adds timers; all129overlapping non-timing records (including candidate tables and payloads) are exactly unchanged.',
           '- Counting, normalization (including rate hashes), selection, ranking serialization, payload checks and tail/member checks are separated in rows.csv. Tail_and_member_check_s includes the final all-member cache validation, not just query replay. Models/scores are preloaded; no end-to-end training or speedup claim is made.',
           '- Runtime bindings are restored after each arm and on exceptions; frozen source hashes checked. The control leaves original population/bucket functions intact. This is a post-freeze new-variant diagnostic, not new MAWI24holdout evidence.',
           '- fp64finite member checks are0but its guarantee remains probabilistic under ideal hashing; normalization does not eliminate fingerprint-collision FN risk.',
           '- No manuscript edit is performed. Evidence and interpretation remain in the experiment/MD.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n');(ROOT/'results/summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    verified=dict(status='verified',arm_records=180,same_format_control_matches=60,normalized_no_repeat_bytewise_matches=32,unchanged_v1_non_timing_records=129,raw_mass_range=[min(raw),max(raw)],member_hits_final=0,source_files=inputs)
    (ROOT/'results/verification.json').write_text(json.dumps(verified,indent=2)+'\n')
    print(json.dumps([s for s in summary if s['cohort']=='all'],indent=2));print('PASS180records;60archived controls;32no-repeat byte matches;129v1records unchanged')


if __name__=='__main__':main()
