"""Separate observed controlled-cost timings from both prediction baselines; stdlib only."""
from pathlib import Path
import json,csv,hashlib,math
from statistics import median
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['timing_records']==288
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    forecast_path=ROOT/'results/pretrial_forecast.json'
    assert sha(forecast_path)==freeze['inputs'][str(forecast_path.relative_to(BLOOM))]
    forecast=json.loads(forecast_path.read_text());assert forecast['status']=='prediction_only_not_measurement'
    for p,h in forecast['source_hashes'].items():assert sha(BLOOM/p)==h,p
    predicted={(r['dataset'],r['extra_us']):r for r in forecast['points']}
    rows=[];points=[];inputs={}
    for ds in freeze['settings']:
        path=ROOT/f'results/{ds}.json';d=json.loads(path.read_text());inputs[path.name]=sha(path)
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json') and d['queries']==200000
        expected={(rep,delay,m) for rep in range(3) for delay in freeze['extra_us'] for m in ('RA6','BF+Cache')}
        assert len(d['timings'])==36 and {(r['rep'],r['delay_us'],r['method']) for r in d['timings']}==expected
        for r in d['timings']:
            assert r['member_fn']==0 and r['same_mask_as_round31'] and r['same_cache_as_round31']
            ref=d['round31_configurations'][r['method']]
            assert r['accepted_mask_sha256']==ref['expected_mask_sha256'] and r['cache_sha256']==ref['expected_cache_sha256']
            assert r['backend_calls']==r['actual_backend_responses']==ref['expected_backend_calls'] and r['fp']==ref['expected_fp']
            assert r['backend_calls']==r['fp']+r['members_found'] and r['members_found']==d['member_queries']
            assert r['requested_extra_ns_total']==r['delay_us']*1000*r['backend_calls']
            assert r['elapsed_ns']>=r['observed_busy_wait_ns_total']>=r['requested_extra_ns_total']
            assert math.isclose(r['ns_per_query'],r['elapsed_ns']/d['queries'],rel_tol=1e-12)
            if r['delay_us']==0:assert r['observed_busy_wait_ns_total']==0 and r['observed_min_wait_ns'] is None
            else:assert r['observed_min_wait_ns']>=r['delay_us']*1000
            rows.append(dict(dataset=ds,budget_kib=d['budget_kib'],**r))
        zero={m:median(r['ns_per_query']/1000 for r in d['timings'] if r['method']==m and r['delay_us']==0) for m in ('RA6','BF+Cache')}
        for delay in freeze['extra_us']:
            arms={m:sorted((r for r in d['timings'] if r['method']==m and r['delay_us']==delay),key=lambda r:r['rep']) for m in ('RA6','BF+Cache')}
            a=[r['ns_per_query']/1000 for r in arms['RA6']];b=[r['ns_per_query']/1000 for r in arms['BF+Cache']]
            ma,mb=median(a),median(b);old=predicted[ds,delay]
            pa=zero['RA6']+arms['RA6'][0]['backend_calls']/d['queries']*delay;pb=zero['BF+Cache']+arms['BF+Cache'][0]['backend_calls']/d['queries']*delay
            points.append(dict(dataset=ds,budget_kib=d['budget_kib'],delay_us=delay,RA_us=ma,BF_us=mb,RA_min_us=min(a),RA_max_us=max(a),BF_min_us=min(b),BF_max_us=max(b),
                               measured_ratio=ma/mb,median_paired_ratio=median(x/y for x,y in zip(a,b)),per_rep_wins=sum(x<y for x,y in zip(a,b)),
                               round31_predicted_RA_us=old['predicted_RA_us'],round31_predicted_BF_us=old['predicted_BF_us'],round31_predicted_ratio=old['predicted_RA_BF_ratio'],
                               current0_predicted_RA_us=pa,current0_predicted_BF_us=pb,current0_predicted_ratio=pa/pb,
                               RA_residual_current0_us=ma-pa,BF_residual_current0_us=mb-pb,
                               RA_mean_actual_wait_us=median(r['observed_mean_wait_ns']/1000 for r in arms['RA6']),BF_mean_actual_wait_us=median(r['observed_mean_wait_ns']/1000 for r in arms['BF+Cache'])))
    assert len(rows)==288 and len(points)==48
    for name,data in (('timings.csv',rows),('curve_points.csv',points)):
        with (ROOT/'results'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    wins=[]
    for delay in freeze['extra_us']:
        pp=[r for r in points if r['delay_us']==delay]
        wins.append(dict(delay_us=delay,old_forecast_wins=sum(r['round31_predicted_ratio']<1 for r in pp),current0_forecast_wins=sum(r['current0_predicted_ratio']<1 for r in pp),
                         measured_median_wins=sum(r['measured_ratio']<1 for r in pp),all_three_repetitions_wins=sum(r['per_rep_wins']==3 for r in pp),settings=8))
    text=['# Artificial backend-cost sensitivity: predictions versus measurements','',
          '**Complete:**288timings,8fixed settings,6prespecified extra-cost levels,2methods,3repetitions. Every insertion follows real SQLiteNonefeedback; artificial waiting is added to EVERYactualSQLresponse, including members. No wait on filter rejects/cache hits. All288masks,FPcounts and finalCache states match round31.','',
          'These are real total-time measurements of local SQLite PLUS an artificial CPU busy-wait service-cost adapter. They are NOT measurements of a real remote database, network latency, cold storage, larger member set, or concurrent service. Python/scalar dispatch and adapter overhead are included.','',
          '## Predicted and observed wins (RA faster than BF+Cache)','',
          '| Extra cost/SQLcall(us) | Prior round31forecast | Contemporary0uscalibration forecast | Observed median wins | Wins in all3paired repetitions |','|---:|---:|---:|---:|---:|']
    for r in wins:text.append(f'| {r["delay_us"]} | {r["old_forecast_wins"]}/8 | {r["current0_forecast_wins"]}/8 | {r["measured_median_wins"]}/8 | {r["all_three_repetitions_wins"]}/8 |')
    text+=['','## Full paired curve','',
           '| Setting | Extraus | RA us/query | BF+Cache us/query | Observed ratio | Prior forecast ratio | Current0forecast ratio | Paired wins/3 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in points:text.append(f'| {r["dataset"]} | {r["delay_us"]} | {r["RA_us"]:.4f} | {r["BF_us"]:.4f} | {r["measured_ratio"]:.4f} | {r["round31_predicted_ratio"]:.4f} | {r["current0_predicted_ratio"]:.4f} | {r["per_rep_wins"]}/3 |')
    positive=[r for r in points if r['delay_us']>0]
    err=[abs(r[k]) for r in positive for k in ('RA_residual_current0_us','BF_residual_current0_us')]
    text+=['','## Model check and limits','',
           f'- With only the contemporary0usintercept calibrated, median absolute residual across the80positive-delay method/setting points is{median(err):.6f}us/query; maximum is{max(err):.6f}us/query. Individual residuals and requested/observed busy-wait costs are retained in curve_points.csv and timings.csv.',
           '- The round31forecast was saved before any new timing. The current0forecast changes only the intercept to this campaign’s0usmeasurement; slopes remain actual backend-call proportions. No fitting to the positive-delay observations or after-the-factdelay-grid extension.',
           '- Measured_median_wins uses the ratio of method medians; median paired ratios and each repetition’s direction are separately retained. Three repeated timings of the same stream are not independent datasets or a significance test. Near1ratios and inconsistent paired directions should not be called stable improvements.',
           '- Additional service cost can make avoided backend calls pay for the model in this controlled setup. It does not prove such costs occur on a particular real backend, nor that this fixed selector is latency-optimal.',
           '- Actual busy-wait spans can overshoot; the total timer also includes clock checks and adapter bookkeeping. Database/CPU cache state, method order and scheduling can make the linear-cost model imperfect. The counts and cache semantics, however, are checked invariant for everyrun.',
           '- Increasing queryNalone cannot turn an existing loss into a win while per-query costs and fixed costs remain unchanged:the difference is affine with positive slope. Changing the working set, repetition, member count or BFload violates that assumption and needs a separate experiment.',
           '- Round31COD has3000000members and159182848database page bytes (~53.060949B/member). Linear extrapolation of file size is not a critical member-count prediction; neither activeworking-set size nor unchanged FP/Cachebehavior follows from a larger file.',
           '- Do not substitute these artificial-cost rows for the original real-backend rows, and do not claim real remote production performance. No manuscript edit was made.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    verification=dict(status='verified',timing_records=288,settings=8,cost_levels=6,all_query_masks_equal_round31=True,all_cache_states_equal_round31=True,member_fn=0,
                      delta_summary=wins,median_abs_current0_residual_us=median(err),max_abs_current0_residual_us=max(err),source_files=inputs)
    (ROOT/'results/verification.json').write_text(json.dumps(verification,indent=2)+'\n');print(json.dumps(wins,indent=2));print('PASS288actual timing records;all query/cache invariants;forecasts kept separate')


if __name__=='__main__':main()
