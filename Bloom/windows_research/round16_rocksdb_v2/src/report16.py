"""Verify and summarize the complete real-Get campaign; stdlib by default."""
import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1]
METHODS=('Direct','BFCache','Gama','RA6','Replay')
WORKLOADS=('zipf','once')
CACHES={'fit':1024**3,'pressure':8*1024**2}


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def check_configuration(r):
    c=r['cache_regime'];cc=r['configuration_check']
    assert r['block_cache_capacity']==CACHES[c]
    assert cc['effective_cache_capacity']==CACHES[c]
    assert cc['explicit_default_column_family'] and cc['cache_object_equals_db_usage']
    assert r['block_cache_usage']>0
    assert cc['bloom_useful_of_2000_misses']>=1900
    assert cc['positive_probe_hit_rate']>=.95 if c=='fit' else cc['positive_probe_hit_rate']<=.2
    if r['method']=='Direct':assert r['rocksdb_statistics_delta']['rocksdb.bloom.filter.useful']>0


def collect(root=ROOT,with_inputs=False,with_latencies=False):
    assert __debug__,'Verification requires assertions'
    bloom=root.parents[1];dest=root/'results/main';tracked={}
    def load(p):
        tracked[str(p.relative_to(bloom))]=digest(p)
        return json.loads(p.read_text())
    manifest=load(root/'results/manifest.json');done=load(dest/'completion.json')
    assert done==dict(status='complete',query_processes=60,construction_processes=3,methods=5,workloads=2,
                      cache_regimes=2,reps=3,manifest_sha256=digest(root/'results/manifest.json'))
    assert manifest['methods']==list(METHODS) and manifest['workloads']==list(WORKLOADS)
    assert manifest['block_caches']==CACHES and manifest['reps']==3
    freeze=load(root/'plan/freeze.json');assert freeze==manifest['freeze']
    for rel,h in freeze['sources'].items():
        assert digest(bloom/rel)==h,rel
        tracked[rel]=h
    database=load(root/'results/database.json');assert database==manifest['database']
    if with_inputs:
        for rel,h in {**freeze['cache_inputs'],**freeze['dependency']}.items():assert digest(bloom/rel)==h,rel
        for rel,h in {**database['inputs_sha256'],**database['sst_sha256']}.items():assert digest(root/rel)==h,rel
    if with_latencies:import numpy as np
    builds={}
    for rep in range(3):
        r=load(root/f'results/filters_rep{rep}.json')
        assert r['status']=='complete' and r['exit_code']==0 and r['rep']==rep
        assert set(r['methods'])=={f'{w}/{m}' for w in WORKLOADS for m in METHODS[1:]}
        builds[rep]=r
    names={f'{w}_{c}_rep{r}_{m}' for w in WORKLOADS for c in CACHES for r in range(3) for m in METHODS}
    assert {p.stem for p in dest.glob('*_rep*_*.json')}==names
    raw=[];groups={};refs={}
    metrics=('seconds','cpu_s','throughput_qps','mean_us','timed_request_mean_us','p50_us','p95_us','p99_us',
             'db_calls','db_negative_misses','cache_hits','filter_rejections','cache_insertions','data_block_hit_rate',
             'block_cache_usage','whole_process_peak_rss_bytes','minor_faults','major_faults')
    for w in WORKLOADS:
        for c in CACHES:
            pairs={}
            for rep in range(3):
                by={}
                for m in METHODS:
                    p=dest/f'{w}_{c}_rep{rep}_{m}.json';r=load(p)
                    assert r['status']=='ok' and r['exit_code']==0 and not r['pilot']
                    assert (r['method'],r['workload'],r['cache_regime'],r['rep'])==(m,w,c,rep)
                    assert (r['queries'],r['positive_queries'],r['negative_queries'])==(166667,16667,150000)
                    assert r['wrong_answers']==r['invalid_values']==r['member_fn_after_run']==0
                    assert r['returned_members']==16667
                    assert r['db_calls']==r['returned_members']+r['db_negative_misses']
                    assert r['db_calls']+r['cache_hits']+r['filter_rejections']==r['queries']
                    assert r['rocksdb_statistics_delta']['rocksdb.number.keys.read']==r['db_calls']
                    check_configuration(r)
                    assert all(math.isfinite(r[k]) and r[k]>=0 for k in metrics)
                    assert 0<r['seconds']<r['process_wall_s']
                    assert math.isclose(r['throughput_qps'],r['queries']/r['seconds'],rel_tol=1e-12)
                    assert math.isclose(r['mean_us'],r['seconds']*1e6/r['queries'],rel_tol=1e-12)
                    assert r['p50_us']<=r['p95_us']<=r['p99_us']
                    counts=r['rocksdb_statistics_delta'];hit=counts.get('rocksdb.block.cache.data.hit',0);miss=counts.get('rocksdb.block.cache.data.miss',0)
                    assert r['data_block_hit_rate']==hit/max(1,hit+miss)
                    lat=p.with_suffix('.latency.npz');assert digest(lat)==r['latency_sha256'];tracked[str(lat.relative_to(bloom))]=digest(lat)
                    if with_latencies:
                        with np.load(lat) as f:a=f['latency_ns']
                        assert a.shape==(166667,) and (a>=0).all()
                        for field,q in (('p50_us',.5),('p95_us',.95),('p99_us',.99)):
                            assert float(np.quantile(a,q)/1000)==r[field]
                        assert float(a.mean()/1000)==r['timed_request_mean_us']
                    log=p.with_suffix('.log');text=log.read_text()
                    assert 'Traceback' not in text and f'QUERY {m} {w} {c} rep{rep}:' in text
                    tracked[str(log.relative_to(bloom))]=digest(log)
                    stats=p.with_suffix('.rocksdb_stats.txt');assert stats.is_file();tracked[str(stats.relative_to(bloom))]=digest(stats)
                    if m=='Direct':
                        assert r['db_calls']==r['queries'] and r['db_negative_misses']==150000 and r['filter']=={}
                        ready=0.
                    else:
                        meta=builds[rep]['methods'][f'{w}/{m}'];assert r['filter']==meta
                        assert meta['fixed_member_checks_passed'] and meta['actual_deployment_array_bytes']<=128*1024
                        assert r['db_negative_misses']==meta['expected_db_negative_misses']
                        assert meta['train_to_ready_s']==sum(meta[k] for k in ('selection_build_s','train_s','score_prepare_s','learning_db_acquire_s','offline_cache_prepare_s'))
                        ready=meta['train_to_ready_s']
                    key=(w,m)
                    if key in refs:
                        for k in ('db_calls','db_negative_misses','cache_hits','filter_rejections','cache_insertions','stream_sha256','input_keys_sha256'):
                            assert r[k]==refs[key][k],(w,c,m,k)
                    else:refs[key]=r
                    by[m]=r
                    raw.append(dict(workload=w,cache_regime=c,rep=rep,method=m,**{k:r[k] for k in metrics},
                                    data_block_hits=hit,data_block_misses=miss,bloom_useful=counts.get('rocksdb.bloom.filter.useful',0),
                                    rocksdb_returned_value_bytes=counts.get('rocksdb.bytes.read',0),
                                    readiness_s=ready,readiness_plus_tail_s=ready+r['seconds'],
                                    external_index_bytes=r['filter'].get('external_member_index_bytes',0)))
                pairs[rep]=by
            groups[w,c]=pairs
    tables=[]
    for (w,c),pairs in groups.items():
        for m in METHODS:
            rr=[r for r in raw if r['workload']==w and r['cache_regime']==c and r['method']==m]
            speed=[pairs[i]['Direct']['seconds']/pairs[i][m]['seconds'] for i in range(3)]
            totalratio=[r['readiness_plus_tail_s']/pairs[r['rep']]['Direct']['seconds'] for r in rr]
            bf_ratio=[pairs[i][m]['seconds']/pairs[i]['BFCache']['seconds'] for i in range(3)]
            breaks=[]
            for r in rr:
                saving=(pairs[r['rep']]['Direct']['seconds']-r['seconds'])/166667
                breaks.append(r['readiness_s']/saving if m!='Direct' and saving>0 else None)
            table=dict(workload=w,cache_regime=c,method=m,medians={k:median(r[k] for r in rr) for k in rr[0] if k not in ('workload','cache_regime','rep','method')},
                       paired_query_speedup_median=median(speed),paired_query_speedups=speed,
                       paired_time_over_bfcache_median=median(bf_ratio),paired_time_over_bfcache=bf_ratio,
                       paired_readiness_plus_tail_ratio_median=median(totalratio),paired_readiness_plus_tail_ratios=totalratio,
                       estimated_break_even_queries=breaks)
            tables.append(table)
    return raw,tables,dict(status='verified',runs=60,checked_raw_inputs=with_inputs,checked_latency_distributions=with_latencies,sources=tracked)


def render(raw,tables):
    lines=['# Real RocksDB point-query integration','',
           '60 fresh query processes; 3 fresh training/selection repetitions. URL-derived membership and precomputed features, synthetic Zipf/unique lookup sequences, 10% true hits. This is not a production database trace.', '',
           'The 841.5MiB read-only SST snapshot retains RocksDB\'s internal 10bits/key Bloom and default compression. Every run warms all members, then checks 2000 member reads and 2000 missing-key reads to verify effective block-cache/Bloom configuration before starting a cold external cache. OS page cache is not cleared. Values are really returned; only a Get returning None permits negative-cache feedback.', '',
           'Times and percentiles below are medians of three independent timing runs. Speedup is the median of paired Direct/method elapsed ratios; it may differ from the ratio of table medians.','']
    for w in WORKLOADS:
        for c in CACHES:
            group=[t for t in tables if t['workload']==w and t['cache_regime']==c]
            lines += [f'## {w}: {c} ({CACHES[c]/2**20:g}MiB RocksDB block cache)','',
                      '| Method | Total s | QPS | Mean µs/query | p95 µs | p99 µs | Get calls | Confirmed negative misses | Paired query speedup |',
                      '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
            for t in group:
                r=t['medians'];lines.append(f"| {t['method']} | {r['seconds']:.3f} | {r['throughput_qps']:.0f} | {r['mean_us']:.3f} | {r['p95_us']:.3f} | {r['p99_us']:.3f} | {r['db_calls']:,} | {r['db_negative_misses']:,} | {t['paired_query_speedup_median']:.3f}× |")
            lines+=['','| Method | Data block hits | Data block misses | Data hit rate | Internal Bloom useful | Readiness s | Readiness+tail s | Total / Direct |',
                    '|---|---:|---:|---:|---:|---:|---:|---:|']
            for t in group:
                r=t['medians'];lines.append(f"| {t['method']} | {r['data_block_hits']:,} | {r['data_block_misses']:,} | {r['data_block_hit_rate']:.2%} | {r['bloom_useful']:,} | {r['readiness_s']:.3f} | {r['readiness_plus_tail_s']:.3f} | {t['paired_readiness_plus_tail_ratio_median']:.3f} |")
            lines.append('')
    lines+=['## RA6 relative to ordinary BF+cache','',
            '| Workload | Cache regime | Paired RA6 / BF+cache query-time ratio |',
            '|---|---|---:|']
    for t in tables:
        if t['method']=='RA6':
            lines.append(f"| {t['workload']} | {t['cache_regime']} | {t['paired_time_over_bfcache_median']:.3f} |")
    lines.append('')
    ra=[t for t in tables if t['method']=='RA6']
    wins=sum(t['paired_query_speedup_median']>1 for t in ra)
    lines+=['## Interpretation','',f'- RA6 query-only speedup versus direct RocksDB has a favorable median in **{wins}/4 settings**. This count is descriptive, not a significance claim. All losses and slow repeats remain in the archive.',
            '- Fewer database-confirmed negative misses do not imply lower latency. RocksDB already screens misses through its own Bloom filters, while external model traversal, safety feedback and Python/Numba calls add work. This integration does not establish the speed of a fused C++ filter inside RocksDB.',
            '- Cache capacity regimes are validated by the reported data-block hit rates, not by their names alone. Data-block misses can be served from the OS page cache. rocksdb.bytes.read counts returned value bytes, not device reads; all original ticker names and snapshots are retained.',
            '- Mean µs/query uses overall wall time divided by request count. Individual p95/p99 include probe/Get/response/update and exclude outer-loop inter-request bookkeeping; they are not batch averages. Full compressed per-query latency arrays are archived and can be checked with --latencies.',
            '- External filters use <=128KiB of owning filter/cache arrays. Verified-prefix cache users additionally require an external member index (8B/member); request features, interpreter/JIT and database block cache are separate. Total process memory is not matched by nominal filter budgets.',
            '- Construction costs include fresh training/scoring for learned methods, method-specific selection/build, and actual acquisition of the 50K learning negatives from RocksDB where required. BF is not charged model cost; Gama is not charged learning feedback. Common learned preparation is charged to each method as if deployed independently. DB creation and JIT are outside readiness.',
            '- timing_summary.json records estimated break-even query counts per repetition only when measured mean query-time saving is positive. Otherwise the value is null: no estimated payback. These estimates assume stationary average cost; they are not observed crossover traces.',
            '- Each readiness+tail total is calculated per repetition before aggregation. This combines measured filter preparation and a measured query campaign, not an uninterrupted database lifetime; the common DB snapshot creation is excluded for all methods.',
            '- The once control has disjoint learning/evaluation negative keys. The workload mixes true member requests into the evaluation only; selectors see the same negative learning sequence. Post-timing labels and correctness-only oracle simulations are never used for live cache admission.',
            '- Database returned members/values, post-run all-member acceptance, raw key hashes, native filter flags and actual key-read ticker counts were checked. The dataset is an immutable snapshot: invalidation after writes and concurrent clients are not evaluated.',
            '- The original round16 campaign is invalid for the intended native-Bloom/cache-capacity protocol: top-level options did not configure the reopened default column family. Its 60 records are retained but excluded. This v2 explicitly passes default-column-family options and aborts unless effective capacity, residency and Bloom activity are verified; no workload, filter or budget was tuned to improve outcomes.']
    buf=io.StringIO(newline='');writer=csv.DictWriter(buf,fieldnames=list(raw[0]));writer.writeheader();writer.writerows(raw)
    return {'report.md':'\n'.join(lines)+'\n','timing_rows.csv':buf.getvalue(),'timing_summary.json':json.dumps(tables,indent=2)+'\n'}


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');p.add_argument('--latencies',action='store_true');p.add_argument('--verify-only',action='store_true');a=p.parse_args()
    rows,table,verified=collect(with_inputs=a.inputs,with_latencies=a.latencies)
    for name,text in render(rows,table).items():
        path=ROOT/'results'/name
        if a.verify_only:assert path.read_bytes()==text.encode(),name
        else:path.write_bytes(text.encode())
    if not a.verify_only:(ROOT/'results/verification.json').write_text(json.dumps(verified,indent=2)+'\n')
    print('PASS: 60 real-Get runs, complete coverage, true-response checks, counters and summary arithmetic')
