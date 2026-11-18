"""Standard-library archival summary for a complete read-only count audit."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[1]
DATASETS=('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow','cod','url','caida','shalla')


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def main(verify_only=False):
    done=json.loads((ROOT/'results/completion.json').read_text())
    assert done==dict(status='complete',main_cases=1146,holdout_cases=4,stream_groups=325,datasets=9)
    records=[];streams=[];inputs={};sources={}
    for ds in DATASETS:
        r=json.loads((ROOT/f'results/{ds}.json').read_text());assert r['status']=='complete' and r['dataset']==ds
        assert all(x['dataset']==ds for x in r['cases'])
        records+=r['cases'];streams+=r['streams'];inputs.update(r['inputs']);sources.update(r['sources'])
    assert len(records)==1150 and len(streams)==325
    assert len({(r['dataset'],r['budget_kib'],r['workload'],r['seed']) for r in records})==1150
    assert len({(r['dataset'],r['workload'],r['seed']) for r in streams})==325
    for rel,h in sources.items():assert digest(ROOT.parents[1]/rel)==h,rel
    for s in streams:
        nc=s['N_c_1_to_6'];g=[c for c in range(1,6) if nc[str(c)]>0 and nc[str(c+1)]==0]
        assert g==s['gap_c']
        assert s['gap_keys']==sum(nc[str(c)] for c in g)
        assert s['gap_learning_queries']==sum(c*nc[str(c)] for c in g)
        assert s['gap_query_share']==s['gap_learning_queries']/s['L']
        if not g:
            assert s['literal_fallback_rate_bit_equal'] and s['original_rate_sha256']==s['literal_rate_sha256']
        if s['all_singletons']:
            assert s['original_unseen_mass']==1 and s['preserve_singleton_fallback_rate_bit_equal']
        sub=[r for r in records if (r['dataset'],r['workload'],r['seed'])==(s['dataset'],s['workload'],s['seed'])]
        assert sorted(r['budget_kib'] for r in sub)==sorted(s['budgets'])
        for r in sub:
            for k in ('L','gap_c','gap_keys','gap_learning_queries','original_rate_sha256','base_stream_sha256'):assert r[k]==s[k]
    tcp=json.loads((ROOT/'results/tcp_supplement.json').read_text());assert tcp['status']=='complete' and len(tcp['cases'])==16
    assert len(tcp['streams'])==4
    assert len({(r['dataset'],r['budget_kib']) for r in tcp['cases']})==16
    for s in tcp['streams']:
        nc=s['N_c_1_to_6'];g=[c for c in range(1,6) if nc[str(c)]>0 and nc[str(c+1)]==0]
        assert g==s['gap_c'] and s['gap_learning_queries']==sum(c*nc[str(c)] for c in g)
        if not g:assert s['literal_fallback_rate_bit_equal'] and s['original_rate_sha256']==s['literal_rate_sha256']
        sub=[r for r in tcp['cases'] if r['dataset']==s['dataset']]
        assert sorted(r['budget_kib'] for r in sub)==sorted(s['budgets'])
        for r in sub:
            for k in ('L','gap_c','gap_keys','gap_learning_queries','original_rate_sha256','base_stream_sha256'):assert r[k]==s[k]
    def counts(rr):
        return dict(cases=len(rr),any_gap=sum(bool(r['gap_c']) for r in rr),
                    all_singletons=sum(r['all_singletons'] for r in rr),
                    non_singleton_gap=sum(bool(r['gap_c']) and not r['all_singletons'] for r in rr),
                    repeated_bin_gap=sum(bool(r['repeated_gap_c']) for r in rr),
                    total_rate_collapse=sum(r['total_collapse'] for r in rr),
                    literal_rates_unchanged=sum(r['literal_fallback_rate_bit_equal'] for r in rr),
                    singleton_preserving_rates_unchanged=sum(r['preserve_singleton_fallback_rate_bit_equal'] for r in rr),
                    total_mass_range=[min(r['original_total_mass'] for r in rr),max(r['original_total_mass'] for r in rr)])
    summary={tag:counts([r for r in records if r['cohort']==tag]) for tag in ('main','holdout')}
    summary['tcp_supplement']=counts(tcp['cases']);summary['stream_groups']=counts(streams)
    lines=['# Frozen Good–Turing count audit: real inputs, no repaired method','',
           'The audit regenerates actual learning streams, verifies their full-base hashes against archived round13 records, and calls the frozen summarize function. No model is trained, no candidate is reranked, and no FP result is replaced. '
           'Budget cases share learning streams:1146 main cases plus4 MAWI-24 cases correspond to325 dataset/workload/seed groups. The16 TCP-only settings are a separately labeled supplement.','',
           '| Cohort | Cases | Any missing-next-bin trigger | All-singleton cases | Non-singleton triggers | Total mass collapse |',
           '|---|---:|---:|---:|---:|---:|']
    for tag in ('main','holdout','tcp_supplement'):
        s=summary[tag];lines.append(f"| {tag} | {s['cases']} | {s['any_gap']} | {s['all_singletons']} | {s['non_singleton_gap']} | {s['total_rate_collapse']} |")
    lines+=['','## Actual real-trace learning prefixes','',
            '| Dataset | Learning negative queries | Gap bins | Affected queries | Original seen+unseen mass |',
            '|---|---:|---|---:|---:|']
    for s in streams+tcp['streams']:
        if s['dataset'].endswith('_flow'):
            lines.append(f"| {s['dataset']} | {s['L']:,} | {s['gap_c']} | {s['gap_learning_queries']} | {s['original_total_mass']:.10f} |")
    lines+=['','## Triggered streams with repeated keys','',
            '| Dataset | Workload | Seed | Budgets | Missing-next bins | Keys affected | Learning queries affected | Query share |',
            '|---|---|---:|---|---|---:|---:|---:|']
    for s in streams:
        if s['gap_c'] and not s['all_singletons']:
            lines.append(f"| {s['dataset']} | {s['workload']} | {s['seed']} | {s['budgets']} | {s['gap_c']} | {s['gap_keys']} | {s['gap_learning_queries']} | {s['gap_query_share']:.9g} |")
    lines+=['','## Conclusions allowed by this audit','',
            '- Missing-next-bin degeneration is real: equal2–5 repeats per key produces zero seen rates and zero unseen mass. An all-singleton prefix is different: seen rates are zero but unseen mass is1 under the original construction.',
            '- Literal fallback for every c<=5 makes an all-singleton prefix assign seen mass1 plus unseen mass1. Simply falling back to c is therefore NOT an unconditional repair of the original contract.',
            '- Preserving the all-singleton special case avoids that particular change, but does not establish calibrated probabilities. The mixed-count example [1,1,2,2] gives total mass4/3 after fallback; [1,2,3,4,5,6] already exceeds1 with no missing-next bin. Missing-bin repair and probability normalization are distinct questions.',
            '- For untriggered inputs the diagnostic fallback array is bit-identical, and its hash is recorded. This is not a new-method rerun or a proof that every existing experiment is unchanged after arbitrary smoothing/renormalization. Changed statistics must be followed through candidate selection and held-out FP before claiming negligible effectiveness impact.',
            '- Main/holdout quality streams contain only neg_test keys by construction; raw labels are excluded before summarize. The summarize function itself has no member-label check and will accept arbitrary integer keys, so it cannot by itself enforce mixed-query semantics.',
            '- Real feedback can reuse a label from a Get that would already occur; this does not make acquiring all negative-learning labels free. Filtered-out requests never call the backend, and logging backend misses alone samples a different stream. Round16 explicitly measures actual learning Gets; source selection costs and label/logging costs must be separated.',
            '- No claims here about unchanged full-table FP totals, the718/748 comparison, repaired selection speedups or a submission-date decision. This audit diagnoses counts, not method quality. Any affected MAWI-24 reselection would be post-hoc, preserving the original frozen holdout results.']
    cols=('cohort','dataset','budget_kib','workload','seed','L','distinct_keys','gap_c','gap_keys','gap_learning_queries','gap_query_share',
          'all_singletons','singleton_gap_with_repeats','original_seen_rate_sum','original_unseen_mass','original_total_mass',
          'literal_fallback_total_mass','preserve_singleton_fallback_total_mass','literal_fallback_rate_bit_equal',
          'preserve_singleton_fallback_rate_bit_equal','total_collapse','base_stream_sha256','original_rate_sha256','literal_rate_sha256')
    buf=io.StringIO(newline='');w=csv.DictWriter(buf,fieldnames=cols,extrasaction='ignore');w.writeheader();w.writerows(records)
    outputs={'report.md':'\n'.join(lines)+'\n','summary.json':json.dumps(summary,indent=2)+'\n','cases.csv':buf.getvalue()}
    for name,text in outputs.items():
        p=ROOT/'results'/name
        if verify_only:assert p.read_bytes()==text.encode(),name
        else:p.write_bytes(text.encode())
    print(json.dumps(summary,indent=2));print('PASS:1150 original/holdout cases,325 stream groups; separate TCP16 supplement')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify-only',action='store_true');main(p.parse_args().verify_only)
