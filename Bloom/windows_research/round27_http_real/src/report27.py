"""Verify every planned real-HTTP result, without excluding losses or low FP counts."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]
sys.path.insert(0,str(ROOT/'src'))
from data27 import sha,save
import json
import csv
from statistics import median


def main():
    done=json.loads((ROOT/'results/completion.json').read_text());assert done['status']=='complete' and done['records']==90
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    rows=[];datasets=[];regions=[];files={}
    for ds in ('nasa_jul95','nasa_aug95'):
        meta=json.loads((ROOT/f'cache/{ds}.json').read_text())
        download=json.loads((ROOT/f'results/data_{ds}_download.json').read_text())
        assert download['status']=='complete_crc_verified' and meta['source_sha256']==download['sha256']
        save(ROOT/f'results/data_{ds}_preparation.json',meta)
        for seed in (2701,2702,2703):
            p=ROOT/f'results/{ds}_{seed}.json';d=json.loads(p.read_text());files[p.name]=sha(p)
            assert d['status']=='complete' and d['seed']==seed and d['dataset']==ds and len(d['rows'])==15
            assert d['input_sha256']==meta['prepared_sha256']
            datasets.append(dict(dataset=ds,seed=seed,members=d['members'],negative_pool=d['negative_pool'],train_negatives=d['train_negatives'],validation_negatives=d['validation_negatives'],
                                 learning_queries=d['learning_queries'],tail_queries=d['tail_queries'],learning_distinct=d['learning_distinct'],tail_distinct=d['tail_distinct'],
                                 auc_tree16=d['auc_by_tree']['16'],auc_tree200=d['auc_by_tree']['200'],negative_feature_overlap=d['negative_keys_sharing_features_with_members'],
                                 backend_index_payload_bytes=d['backend_index_payload_bytes']))
            expected={(k,m) for k in (4,8,16) for m in ('Gama','Replay','RA-global','RA-PLBF-GT19','BF+Cache')}
            assert {(r['budget_kib'],r['method']) for r in d['rows']}==expected
            for r in d['rows']:
                assert r['member_fn']==0 and r['processed']==d['tail_queries'] and 0<=r['fp']<=r['processed']
                total=sum(r[k] for k in ('model_payload_bytes','bf_payload_bytes','metadata_bytes','array_overhead_bytes','cache_physical_bytes'))
                assert total==r['total_bytes']<=r['budget_kib']*1024
                base=next(x for x in d['rows'] if x['budget_kib']==r['budget_kib'] and x['method']=='BF+Cache')
                rp=next(x for x in d['rows'] if x['budget_kib']==r['budget_kib'] and x['method']=='Replay')
                rows.append(dict(dataset=ds,seed=seed,**{k:r[k] for k in ('budget_kib','method','trees','cache_frac','fp','hits','evictions','bypasses','occupied','total_bytes','unused_bytes','model_payload_bytes','bf_payload_bytes','metadata_bytes','array_overhead_bytes','cache_physical_bytes','backend_member_index_payload_bytes','build_and_select_s','tail_replay_s')},
                                 ratio_to_BF_cache=(r['fp']+1)/(base['fp']+1),ratio_to_Replay=(r['fp']+1)/(rp['fp']+1),tail_queries=d['tail_queries']))
                if r['region_diagnostics']:
                    z=r['region_diagnostics'];assert sum(v['learning_requests'] for v in z)==d['learning_queries'] and sum(v['tail_requests'] for v in z)==d['tail_queries']
                    regions += [dict(dataset=ds,seed=seed,budget_kib=r['budget_kib'],method=r['method'],**v) for v in z]
    assert len(rows)==90
    for name,rr in (('rows.csv',rows),('datasets.csv',datasets),('region_repetition.csv',regions)):
        with (ROOT/'results'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rr[0]));w.writeheader();w.writerows(rr)
    text=['# Real HTTP missing-resource requests: full results','',
          'NASA KSC July/August1995. Real chronological GET404 requests, not synthesized popularity. Model sees20lexical URL/path features, no protocol/status/response-size/time/frequency features. All5methods share each physical budget and held-out negative tail.','',
          '**Scope:** retrospective static-stable-resource subset. The full month defines the successful-resource catalog and excludes success/404 conflicts. Therefore this is NOT a prospective mutable-site or real-backend latency benchmark. Train/validation negative keys are prefix-only and disjoint from query-pool keys; fresh tail keys are not used to train.','',
          '## Data construction and exclusions','',
          '| Month | Parsed GET | Stable members | Stable absent keys | Actual retained404requests | Conflicting keys excluded |404requests excluded for conflicts |','|---|---:|---:|---:|---:|---:|---:|']
    for ds in ('nasa_jul95','nasa_aug95'):
        m=json.loads((ROOT/f'results/data_{ds}_preparation.json').read_text())
        text.append(f'| {ds} | {m["parsed_GET"]} | {m["members"]} | {m["negatives"]} | {m["retained_404_requests"]} | {m["conflicting_keys"]} | {m["conflicting_404_requests"]} |')
    text+=['','## Learning and held-out diagnostics','',
           '| Month | Seed | Learn requests/distinct | Tail requests/distinct |16-tree AUC |200-tree AUC | Negative keys sharing exact feature vectors with members |',
           '|---|---:|---|---|---:|---:|---:|']
    for d in datasets:text.append(f'| {d["dataset"]} | {d["seed"]} | {d["learning_queries"]}/{d["learning_distinct"]} | {d["tail_queries"]}/{d["tail_distinct"]} | {d["auc_tree16"]:.4f} | {d["auc_tree200"]:.4f} | {d["negative_feature_overlap"]} |')
    text+=['','## All budgets: medianFP across3paired split/hash seeds','',
           'These are conditional repetitions of the same logs, not6independent workloads. Medians are descriptive; raw paired counts and ratios are in rows.csv. No >=30FP inclusion threshold.','',
           '| Month | KiB | Gama | Replay | RA-global | RA-PLBF-GT19 | BF+Cache | RA/BF+Cache median paired ratio | RA/Replay median paired ratio |','|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    summary=[]
    methods=('Gama','Replay','RA-global','RA-PLBF-GT19','BF+Cache')
    for ds in ('nasa_jul95','nasa_aug95'):
        for kib in (4,8,16):
            rr=[r for r in rows if r['dataset']==ds and r['budget_kib']==kib];ra=[r for r in rr if r['method']=='RA-PLBF-GT19']
            fps={m:median(r['fp'] for r in rr if r['method']==m) for m in methods}
            b=median(r['ratio_to_BF_cache'] for r in ra);p=median(r['ratio_to_Replay'] for r in ra)
            text.append(f'| {ds} | {kib} | '+ ' | '.join(str(fps[m]) for m in methods)+f' | {b:.4f} | {p:.4f} |')
            summary.append(dict(dataset=ds,budget_kib=kib,median_fp=fps,median_RA_BF_ratio=b,median_RA_Replay_ratio=p))
    text+=['','## Interpretation and boundaries','',
           '- The original candidate grid remains learned-only. The no-model method is an explicit comparator, not a hidden fallback. No repetition-to-Gama property is asserted for an expanded selector.',
           '- Region repetition diagnostics use each learned candidate’s fixed regions and preserve both learning and tail descriptive values. Tail values are reported only after selection, not used to pick configurations.',
           '- AUC/feature overlap establish a non-protocol classification task, but do not by themselves establish a learned-filter or reweighting advantage. Compare RA to BF+Cache AND to Replay/RA-global at each matched budget; retain all losses.',
           '- Memory breakdown includes real model arrays, BF bytes, layout/header overhead, allocated cache and unused bytes. The separate8*n backend verification index remains outside the filter budget; fp64 semantics are audited separately in round29.',
           '- Training/scoring/index/build/selection/replay wall times are recorded. One timed execution per configuration with shared preparation is NOT a controlled latency/speedup experiment. Native per-query feature extraction/backend Get timing is not measured here.',
           '- These old NASA logs are small, historical and only one site. They cannot alone establish modern production applicability. Sparse404counts and fitting the working set in BF+Cache can make model overhead unhelpful. Such outcomes are not excluded.',
           '', 'Sources: https://ita.ee.lbl.gov/html/contrib/NASA-HTTP.html ; August mirror https://github.com/COM6012/ScalableML/blob/master/Data/NASA_access_log_Aug95.gz . Download receipts retain gzip CRC checks and SHA256; failed partial downloads are not used as complete data.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    save(ROOT/'results/summary.json',summary);save(ROOT/'results/verification.json',dict(status='verified',jobs=6,method_rows=90,source_files=files))
    print(json.dumps(summary,indent=2),flush=True)
    print('PASS:90method rows, all physical budgets and member/cache checks',flush=True)


if __name__=='__main__':main()
