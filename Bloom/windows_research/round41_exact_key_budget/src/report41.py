import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data41 import ROOT,W,check
import json,csv,statistics


def report():
    check();workers=[json.loads((ROOT/f'results/seed{s}.json').read_text()) for s in (3601,3602,3603)]
    assert all(w['status']=='complete' and len(w['rows'])==39 for w in workers)
    rows=[dict(seed=w['seed'],**r) for w in workers for r in w['rows']]
    for r in rows:
        assert r['auxiliary_total_bytes']<=r['auxiliary_ceiling_bytes']
        assert r.get('mixed_member_fn',0)==0 and r.get('final_member_cache_hits',0)==0
    assert sum(r.get('regression_round37',False) for r in rows)==18
    fields=sorted(set().union(*(r.keys() for r in rows)))
    with (ROOT/'results/rows.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for r in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False,sort_keys=True) if isinstance(v,dict) else v for k,v in r.items()})
    pairs={}
    for a,b in [('RA6-Exact128','BF+Exact128'),('RA6-Exact128','Replay-Exact128'),('ZGate-Exact128','BF+Exact128'),('ZGate-Exact128','RA6-Exact128'),('RA6-prefix','PlainBF-RAactual'),('RA6-prefix','DirectHashIndex')]:
        aa={(r['seed'],r['base_budget_kib']):r for r in rows if r['method']==a};bb={(r['seed'],r['base_budget_kib']):r for r in rows if r['method']==b};assert aa.keys()==bb.keys()
        pairs[a+'/'+b]=dict(wins=sum(aa[k]['fp']<bb[k]['fp'] for k in aa),ties=sum(aa[k]['fp']==bb[k]['fp'] for k in aa),losses=sum(aa[k]['fp']>bb[k]['fp'] for k in aa),median_smoothed_ratio=statistics.median((aa[k]['fp']+1)/(bb[k]['fp']+1) for k in aa))
    summary=dict(status='verified',rows=len(rows),regressions=18,paired_comparisons=pairs,worker_wall_s=sum(w['wall_s'] for w in workers),raw_keys_published=False,modern_production_kv_evidence=False)
    W.save(ROOT/'results/verification.json',dict(**summary,worker_sha256={f'seed{w["seed"]}.json':W.sha(ROOT/f'results/seed{w["seed"]}.json') for w in workers}))
    W.save(ROOT/'results/summary.json',summary)
    text=['# Round41: exact raw-key cache and fair auxiliary memory','', 'This is a new static exact-key variant and a retrospective ClarkNet control, NOT modern production KV evidence. All complete original negative tails and natural mixed tails retained. Timing is replay, NOT service latency.','', '| Method | 8KiB FP median | 16KiB | 32KiB |','| --- | ---: | ---: | ---: |']
    for method in dict.fromkeys(r['method'] for r in rows):
        vals=[statistics.median(r['fp'] for r in rows if r['method']==method and r['base_budget_kib']==k) for k in (8,16,32)]
        text.append('| '+method+' | '+' | '.join(map(str,vals))+' |')
    text+=['','## Paired comparisons','', '| A / B | wins/ties/losses | median (FP_A+1)/(FP_B+1) |','| --- | --- | ---: |']
    for pair,p in pairs.items():text.append(f'| {pair} | {p["wins"]}/{p["ties"]}/{p["losses"]} | {p["median_smoothed_ratio"]:.8f} |')
    text+=['','## Budget and correctness boundaries','', 'Exact128 stores complete raw keys of length<=128; longer keys bypass. Hash only selects a bucket. Byte equality, not fingerprint equality, certifies a hit. The guarantee assumes static membership and truthful exact-backend absence; updates require invalidation. Forced-hash-alias tests must pass. This variant changes cache capacity, so its selection/FP results cannot be attributed to unmodified RA6.','','The prefix index is8*n+array-header bytes when required, not free. Envelope baselines get base budget+index; PlainBF-RAactual gets exactly the actual indexed-RA auxiliary total. DirectHashIndex uses the same sorted hashes, rejects only hash absence and still requires exact-backend lookup on hash presence. These controls equalize auxiliary memory, NOT whole-database memory/RSS or placement/latency. A frontend direct index is not interchangeable with a remote backend index.','','Exact replay workers hold shared offline inputs and verification arrays, including a member index for separate prefix controls; the exact-cache query primitive itself takes neither an index nor a key-dictionary reference. Input key blobs, traces, model training and NumPy/Python workspaces remain separately charged as preparation/harness, not magically eliminated.','','ZGate selects on learning only, tie goes to BF, and pays both searches plus RA replay. No future-tail no-regret, no original no-repeat guarantee, no automatic selection speedup. Long-key bypass is not modeled exactly by the unchanged RA6 heuristic.','','All18 original indexed RA/BF regressions pass. Same source log under3seeds×3budgets is not9independent workloads. No significance or universal model-value claim.','']
    (ROOT/'results/report.md').write_text('\n'.join(text));print(json.dumps(summary,indent=2),flush=True)

if __name__=='__main__':report()
