"""Stdlib-only read-only checks of rounds32--34, including the stopped GT attempt."""
from pathlib import Path
import json,hashlib,math
ROOT=Path(__file__).resolve().parents[1]
NAMES=('round32_no_repeat_guard','round33_gt_normalization','round33_gt_normalization_v2','round34_backend_cost')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())


def main():
    for name in NAMES:
        p=ROOT/'windows_research'/name;f=load(p/'plan/freeze.json')
        for rel,h in f['sources'].items():assert sha(ROOT/rel)==h,(name,rel)
        archive=load(p/'archive_manifest.json')
        for rel,h in archive['files'].items():assert sha(p/rel)==h,(name,rel)
        if name=='round33_gt_normalization':
            assert archive['status']=='stopped_incomplete' and not (p/'results/completion.json').exists()
            assert load(p/'results/stopped_for_timing_fix.json')['saved_arm_records']==129
        else:assert archive['status']=='complete' and load(p/'results/completion.json')['status']=='complete'
    p=ROOT/'windows_research/round32_no_repeat_guard/results';total=0
    for ds in ('cod','url','caida','shalla'):
        d=load(p/f'{ds}.json');assert d['status']=='complete';total+=len(d['cases'])
        refs={r['budget_kib']:r for r in d['reference_budgets']}
        for r in d['cases']:
            assert r['member_fn']==0 and r['gama_payload_bit_equal'] and r['original_RA6_FP_equal'] and r['original_Gama_FP_equal']
            assert r['payload']['hashes']==refs[r['budget_kib']]['hashes'] and r['cache_bytes']==0
        assert d['repeated_control']['payload_bit_equal'] and d['repeated_control']['new_info']['path']=='unchanged_RA6'
    assert total==140
    p=ROOT/'windows_research/round33_gt_normalization_v2/results';done=load(p/'completion.json');total=0;nr=0
    for job in done['jobs']:
        d=load(p/f'{job["dataset"]}_{job["cache"]}.json');assert d['status']=='complete'
        for c in d['cases']:
            for name,r in c['arms'].items():
                total+=1;assert r['member_hits_final']==0 and r['total_bytes']<=c['budget_kib']*1024
                if name!='GT19':
                    assert abs(r['info']['normalization']['total_mass']-1)<1e-12
                    if c['cohort']=='no_repeat':assert r['same_payload_as_GT19'] and r['fp']==c['arms']['GT19']['fp'];nr+=1
                assert math.isclose(r['info']['normalize_and_select_s'],r['info']['normalization_s']+r['info']['selector_wall_s'],rel_tol=1e-12)
    assert total==180 and nr==32
    assert load(p/'verification.json')['unchanged_v1_non_timing_records']==129
    p=ROOT/'windows_research/round34_backend_cost/results';done=load(p/'completion.json');total=0
    for job in done['jobs']:
        d=load(p/f'{job["dataset"]}.json');assert d['status']=='complete';total+=len(d['timings'])
        assert {(r['rep'],r['delay_us'],r['method']) for r in d['timings']}=={(rep,delay,m) for rep in range(3) for delay in (0,5,10,25,50,100) for m in ('RA6','BF+Cache')}
        for r in d['timings']:
            old=d['round31_configurations'][r['method']]
            assert r['accepted_mask_sha256']==old['expected_mask_sha256'] and r['cache_sha256']==old['expected_cache_sha256'] and r['member_fn']==0
            assert r['backend_calls']==r['actual_backend_responses']==old['expected_backend_calls']
            assert r['elapsed_ns']>=r['observed_busy_wait_ns_total']>=r['requested_extra_ns_total']==r['backend_calls']*r['delay_us']*1000
    assert total==288
    v=load(p/'verification.json');assert [r['measured_median_wins'] for r in v['delta_summary']]==[0,0,1,3,5,6]
    print('PASS: NR32 140no-repeat+4repeated; GTv2 180arms/32no-repeat; stopped129retained; artificial-cost288timings')
    print('Read-only: no data download, experiment rerun, manuscript edit or repository sync.')


if __name__=='__main__':main()
