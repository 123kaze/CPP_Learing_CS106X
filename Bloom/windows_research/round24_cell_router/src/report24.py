"""Small static cell-router report, stdlib only."""
import hashlib
import json
import math
from pathlib import Path
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1]


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    freeze=json.loads((ROOT/'plan/freeze.json').read_text())
    for rel,h in freeze['sources'].items():assert digest(BLOOM/rel)==h,rel
    r=json.loads((ROOT/'results/rows.json').read_text());assert r['status']=='complete'
    assert r['openblas_threads']==r['numba_threads']==1
    rows=r['rows'];assert len(rows)==24
    wanted={(ds,b,k,rep) for ds,kk in (('url',(64,128)),('caida_tcp_flow',(16,32))) for b in (16,32) for k in kk for rep in range(3)}
    assert {(v['dataset'],v['bins_per_feature'],v['budget_kib'],v['rep']) for v in rows}==wanted
    lines=['# Direct cell-region table: static first test','',
           'Two predetermined features; quantile bins fit on training rows, cell routing/order fitted with full known members and validation negatives. No negative cache, no residual-cost weights, no raw URL n-grams or IP-prefix reconstruction. Table lookup is3bits/cell, but bin edges, layout, array headers and BF navigation are all charged.','',
           '| Dataset | Grid | KiB | Table FP | PlainBF FP | Full router bytes | Route ns/key | Route+BF ns/key | Fit/build s |',
           '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    for ds,kk in (('url',(64,128)),('caida_tcp_flow',(16,32))):
        for b in (16,32):
            for k in kk:
                rr=[x for x in rows if (x['dataset'],x['bins_per_feature'],x['budget_kib'])==(ds,b,k)]
                assert len(rr)==3 and len({x['flags_sha256'] for x in rr})==1
                for x in rr:
                    assert x['members_verified'] and x['native_matches_frozen_flags']
                    assert x['total_bytes']<=k*1024
                    assert x['total_bytes']==x['packed_table_payload_bytes']+x['bin_edges_payload_bytes']+x['filter_payload_bytes']+x['metadata_and_headers_bytes']
                    assert all(math.isfinite(v) and v>0 for v in x['filter_ns_all']+x['router_ns_all'])
                    assert x['filter_ns_median']==median(x['filter_ns_all']) and x['router_ns_median']==median(x['router_ns_all'])
                x=rr[0]
                lines.append(f"| {ds} | {b}×{b} | {k} | {x['fp']:,} | {x['bf_reference_fp']:,} | {x['router_bytes']} | {median(v['router_ns_median'] for v in rr):.1f} | {median(v['filter_ns_median'] for v in rr):.1f} | {median(v['fit_build_s'] for v in rr):.4f} |")
    lines+=['','## Interpretation','',
            '- The table is cheap to evaluate, but these two features lose substantial URL discrimination relative to the round23 full-feature classifiers. All tested TCP configurations still have more FP than plainBF. This is not evidence about all feature partitions or richer routing schemes.',
            '- The claimed “cells ×3bits” is only table payload:256 cells use96 bytes and1024 cells use384 bytes. Complete routers cost696 and1240 bytes including thresholds/layout/headers, before region BF navigation.',
            '- Known-density likelihood-ratio quantization results motivate ratio ordering, but sample smoothing, physical overhead, PASS clipping and integer BF break a simple exact net-KL deployment criterion. Only a smoothed final-region diagnostic KL is recorded; no guarantee of global resource/latency optimality.',
            '- Timings are native per-key computation inside a batch-amortized loop, including two bin searches and packed lookup. They exclude raw feature extraction and key hashing, and are not Python API latency or end-to-end database latency. Cross-round times are a screening comparison, not paired causal speedups.',
            '- Three deterministic builds use identical data and hyperparameters. All cases retained; no evaluation-guided choice of features/grid or retuning. Protocol/source hashes remain frozen.',
            '- Proposal A (residual-cost-weighted training) and C (raw n-grams) are not implemented in this test. The user\'s requested new experiment branch isolates this work from frozen RA6 and published main.']
    (ROOT/'results/report.md').write_text('\n'.join(lines)+'\n')
    print('PASS:24 cell-table configurations, exact native/BF checks, physical-byte and timing arithmetic')


if __name__=='__main__':main()
