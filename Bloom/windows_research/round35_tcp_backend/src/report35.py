"""Strict completed-case verification of the local TCP experiment; no remote-system claims."""
from pathlib import Path
import json,csv,hashlib
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text());done=json.loads((ROOT/'results/completion.json').read_text())
    assert done['status']=='complete' and done['formal_timing_rows']==72
    for p,h in freeze['sources'].items():assert sha(BLOOM/p)==h,p
    gate=json.loads((ROOT/'results/pilot_gate.json').read_text());assert gate['status']=='passed' and gate['correctness_verified'] and gate['pilot_rows']==6
    rows=[];summary=[];inputs={};resource_rows=[]
    for ds,kib in freeze['settings'].items():
        path=ROOT/f'results/main/{ds}.json';d=json.loads(path.read_text());inputs[str(path.relative_to(ROOT))]=sha(path)
        assert d['status']=='complete' and not d['pilot'] and d['queries']==200000 and d['native_threads']==1
        assert d['freeze_sha256']==sha(ROOT/'plan/freeze.json') and len(d['timings'])==9
        assert {(r['method'],r['rep']) for r in d['timings']}=={(m,n) for m in ('NoFilter','BF+Cache','RA6') for n in range(3)}
        prior=json.loads((WR/f'round31_sqlite_online/results/{ds}.json').read_text())
        assert d['request_sha256']==prior['request_sha256'] and d['backend']['host']=='127.0.0.1' and d['backend']['tcp_nodelay']
        assert d['backend']['index_payload_bytes']==8*d['members'] and d['backend']['native_threads']==1
        for r in d['timings']:
            server=r['server_statistics'];assert r['member_fn']==0 and r['query_mask_equal'] and r['cache_bytes_equal']
            assert r['members_found']==d['member_queries'] and r['backend_calls']==r['fp']+r['members_found']==server['sql_calls']
            assert server['found']==r['members_found'] and server['absent']==r['fp'] and server['prefix_queries']==(r['fp'] if r['need_backend_prefix'] else 0)
            assert r['query_sent_bytes']==9*r['backend_calls'] and r['query_received_bytes']==8*r['backend_calls']+32*r['members_found']
            if r['method']!='NoFilter':
                ref=prior['methods'][r['method']]
                assert r['accepted_mask_sha256']==ref['expected_mask_sha256'] and r['cache_sha256']==ref['expected_cache_sha256']
                assert r['fp']==ref['expected_fp'] and r['backend_calls']==ref['expected_backend_calls']
            else:assert r['backend_calls']==200000 and server['prefix_queries']==0
            rows.append(dict(dataset=ds,budget_kib=kib,method=r['method'],rep=r['rep'],ns_per_query=r['ns_per_query'],elapsed_ns=r['elapsed_ns'],client_cpu_ns=r['client_cpu_ns'],
                             server_cpu_ns=server['cpu_since_reset_ns'],backend_calls=r['backend_calls'],fp=r['fp'],members_found=r['members_found'],cache_hits=r['cache_hits'],
                             server_prefix_queries=server['prefix_queries'],query_sent_bytes=r['query_sent_bytes'],query_received_bytes=r['query_received_bytes'],
                             accepted_mask_sha256=r['accepted_mask_sha256'],cache_sha256=r['cache_sha256']))
        values={m:median(r['ns_per_query']/1000 for r in d['timings'] if r['method']==m) for m in ('NoFilter','BF+Cache','RA6')}
        a={r['rep']:r['ns_per_query'] for r in d['timings'] if r['method']=='RA6'};b={r['rep']:r['ns_per_query'] for r in d['timings'] if r['method']=='BF+Cache'}
        summary.append(dict(dataset=ds,budget_kib=kib,NoFilter_us=values['NoFilter'],BF_cache_us=values['BF+Cache'],RA_us=values['RA6'],RA_BF_ratio=values['RA6']/values['BF+Cache'],
                            RA_NoFilter_ratio=values['RA6']/values['NoFilter'],RA_BF_paired_wins=sum(a[n]<b[n] for n in range(3))))
        resource_rows.append(dict(dataset=ds,members=d['members'],client_peak_rss_bytes=d['client_peak_rss_bytes'],server_peak_rss_bytes=max(r['server_statistics']['peak_rss_bytes'] for r in d['timings']),
                                  server_index_payload_bytes=d['backend']['index_payload_bytes'],server_index_physical_bytes=d['backend']['index_physical_bytes'],
                                  sqlite_page_bytes=d['backend']['page_count']*d['backend']['page_size'],database_build_s=d['backend']['database_build_s'],index_build_s=d['backend']['index_build_s']))
    assert len(rows)==72
    for name,data in (('timings.csv',rows),('summary.csv',summary),('resources.csv',resource_rows)):
        with (ROOT/'results'/name).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    win_b=sum(r['RA_BF_ratio']<1 for r in summary);win_n=sum(r['RA_NoFilter_ratio']<1 for r in summary);stable=sum(r['RA_BF_paired_wins']==3 for r in summary)
    text=['# Independent-process SQLite over local TCP','',
          '**Completed:**8settings ×3methods ×3repetitions=72formal timings, after6prespecified pilot rows passed. No artificial waiting or network delay was added. The server is a separate process bound only to127.0.0.1; this is NOT a cross-machine or production Redis/PostgreSQL benchmark.','',
          'The server performs an actual SQL lookup for every request. Only an absent result for GET_WITH_PREFIX triggers its backend-owned safety index. NoFilter uses plainGET and is not charged unnecessary prefix work. The live client uses only the actual TCP response; its Filter object contains neither labels nor the full member index.','',
          '| Dataset | KiB | NoFilter us/query | BF+Cache | RA-PLBF | RA/BF | RA/NoFilter | RA faster in paired reps |','|---|---:|---:|---:|---:|---:|---:|---:|']
    for r in summary:text.append(f'| {r["dataset"]} | {r["budget_kib"]} | {r["NoFilter_us"]:.4f} | {r["BF_cache_us"]:.4f} | {r["RA_us"]:.4f} | {r["RA_BF_ratio"]:.5f} | {r["RA_NoFilter_ratio"]:.5f} | {r["RA_BF_paired_wins"]}/3 |')
    text+=['',f'RAhas lower median query time than BF+Cache in{win_b}/8settings and NoFilter in{win_n}/8; it is faster than BF+Cache in all3paired repetitions in{stable}/8settings. These are repeated measurements of fixed streams, not independent-sample significance tests.','',
           '## Correctness and measurement scope','',
           '- All72complete accepted masks,FP counts and final packed caches match the original reference. Server SQL/found/absent/prefix counters independently agree with client counts. All finite member checks are0FN.',
           '- BothTCP endpoints useTCP_NODELAY; one persistent connection and one outstanding request, no batching or concurrency-throughput claim. Application request/reply byte counts excludeTCP/IPheaders. Main timing is full-streamwall/N, not per-queryp50/p99.',
           '- Prefix computation is physically on the server after SQLNone; full index payload8*n andarray header are separately listed. The client verification harness retains its own offline reference data outside the timed path; neither client nor server processRSS is claimed to fit Filter Budget.',
           '- This is a custom SQLite RPC service with an explicit index sidecar, not a capability attributed to unmodified Redis/PostgreSQL. NoFilter/plainGETavoids prefix computation, while both cached methods pay for it when needed.',
           '- Model/feature/hash preparation and DB/index construction are outside query timing and separately recorded. Client and serverCPU andRSS are separately available; serverCPU snapshots include small control/statistics overhead and are not isolated SQL service-time measurements.',
           '- Local loopback introduces real process/serialization/socket overhead but not real remote network hops, TLS, WAN variability, production queues or cold storage. Benefits or failures here cannot fill the cross-machine deployment evidence gap.',
           '- Pilot passed based on correctness and conservative duration/resources, not relative RA wins. Formal methods rotate order and reset only frontend caches; database warm state is documented. All repetitions and losses are retained.',
           '- No paper is modified; the original frozen studies and submission tag are not replaced.']
    (ROOT/'results/report.md').write_text('\n'.join(text)+'\n')
    verification=dict(status='verified',formal_rows=72,pilot_rows=6,settings=8,all_masks_equal=True,all_caches_equal=True,all_server_counters_match=True,member_fn=0,
                      RA_median_wins_vs_BF=win_b,RA_median_wins_vs_NoFilter=win_n,RA_all_three_wins_vs_BF=stable,scope='local_loopback_only_no_artificial_delay',source_files=inputs)
    (ROOT/'results/verification.json').write_text(json.dumps(verification,indent=2)+'\n');print(json.dumps(verification,indent=2))


if __name__=='__main__':main()
