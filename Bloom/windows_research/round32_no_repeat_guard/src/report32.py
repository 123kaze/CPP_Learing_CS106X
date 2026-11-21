"""Read-only result checks and a report; old algorithm/theorem is not silently changed."""
from pathlib import Path
import hashlib,json,csv
from statistics import median
ROOT=Path(__file__).resolve().parents[1];BLOOM=ROOT.parents[1];WR=ROOT.parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    f=json.loads((ROOT/'plan/freeze.json').read_text());done=json.loads((ROOT/'results/completion.json').read_text())
    assert done['status']=='complete' and done['no_repeat_cases']==140 and done['repeated_controls']==4
    for p,h in f['sources'].items():assert sha(BLOOM/p)==h,p
    rows=[];controls=[];sources={}
    for ds,budgets in f['settings'].items():
        path=ROOT/f'results/{ds}.json';d=json.loads(path.read_text());sources[path.name]=sha(path)
        assert d['status']=='complete' and d['freeze_sha256']==sha(ROOT/'plan/freeze.json')
        refs={r['budget_kib']:r for r in d['reference_budgets']}
        expected={(k,w,s) for k in budgets for w in ('每key一次','全新对抗') for s in range(5)}
        assert {(r['budget_kib'],r['workload'],r['seed']) for r in d['cases']}==expected
        for r in d['cases']:
            assert r['member_fn']==0 and r['gama_payload_bit_equal'] and r['original_Gama_FP_equal'] and r['original_RA6_FP_equal']
            assert r['cache_bytes']==0 and r['total_bytes']<=r['budget_kib']*1024 and r['selection_info']['path']=='exact_Gama'
            ref=refs[r['budget_kib']]
            for key in ('trees','cache_bytes','total_bytes','hashes','member_fn'):assert r['payload'][key]==ref[key]
            rows.append(dict(dataset=ds,**{k:r[k] for k in ('budget_kib','workload','seed','learning_queries','tail_queries','fp','trees','total_bytes','count_s','select_build_s','payload_check_s','tail_eval_s')}))
        c=d['repeated_control'];assert c['payload_bit_equal'] and c['new_info']['path']=='unchanged_RA6';controls.append(dict(dataset=ds,**c))
    assert len(rows)==140 and len(controls)==4
    with (ROOT/'results/rows.csv').open('w',newline='') as out:w=csv.DictWriter(out,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    lines=['# RA6-NR32: explicit no-repeat Gama dispatch','',
           '**Complete:**140original no-repeat cases reproduce both original Gama and RA6 tailFP, and independently rebuilt Gama deployment arrays match byte for byte during execution. Four repeated controls delegate to original RA6 and reproduce its payload/FP.','',
           'This is a new post-hoc variant, not a repair claimed to have existed before the MAWI24freeze. No original algorithm, main table, cancelled experiment or paper was edited by this round.','',
           '## Conditional implementation guarantee','',
           'For valid finite inputs with a nonempty learning period, a deterministic shared builder and at least one feasible no-cache candidate:','',
           '1. The guard checks raw counts:the number of keys equalsL and every count is1. It does not infer no-repeat from approximate rate mass.',
           '2. In that branch it calls frozen E5.candidates with exactly the same tree grid and frac=0. The zero-cache candidates are the same subset used by E5.gama in the full grid; no cache candidate build mutates their inputs.',
           '3. It selects by that same E5.gama function, including its (estimatedFPR,treecount) tie-breaking, and returns the selected already-built candidate. Therefore it cannot substitute RA’s differently masked score or top5 ranking.',
           '4. For repeated input it passes the same setup,scores,learning summary,budget,H andtopk to frozen ra6.select6 and returns that object. Only reporting metadata changes.',
           '', 'Thus exact selection equivalence is by shared code path for NR32. It is NOT a proof of universal equivalence for unmodified RA6, whose scoring mismatch remains documented. The bounded18-case search in round30 found no counterexample; this round does not relabel that negative search as a counterexample.',
           '', '## Executed regression','', '| Dataset | No-repeat cases | Bit-equal/FP-equal | Median guard select+build(s) | Repeated control FP |','|---|---:|---:|---:|---:|']
    for c in controls:
        rr=[r for r in rows if r['dataset']==c['dataset']]
        lines.append(f'| {c["dataset"]} | {len(rr)} | {len(rr)} | {median(r["select_build_s"] for r in rr):.4f} | {c["fp"]} |')
    lines+=['','## Verification and limits','',
            '- Execution compares actual contiguous uint8 views with numpy.array_equal, plus shapes/dtypes and configuration; hashes are retained for archive checking, not substituted for the live byte comparison. PackedBF is rebuilt and all members checked; all query-pool flags match.',
            '- CSV timing separates counting,selection/build,payload checking andtail evaluation. Models/scores are preloaded, not trained in this timer. No new speedup claim is inferred from one sequential timing percase.',
            '- Fresh-adversarial seedlabels can denote the same deterministic stream. Cases share models and data;140is not140independent samples. No MAWI24result was regenerated or relabeled as a new holdout.',
            '- NR32 does not add zero trees and does not guarantee futureFP optimality, BF+Cache non-regression or lower latency. RA6-ZGate remains a distinct replay-cost variant.',
            '- Empty learning inputs are explicitly rejected. This is not an assertion that the old code had a defined result forL=0.',
            '- Manuscript advice: either state candidate-wise weight reduction/empirical equality for the old implementation, or explicitly label the new dispatch variant and its post-freeze date when claiming a universal same-Gama selection guarantee.']
    (ROOT/'results/report.md').write_text('\n'.join(lines)+'\n')
    summary=dict(status='verified',no_repeat_cases=140,live_bytewise_matches=140,original_Gama_FP_matches=140,original_RA6_FP_matches=140,repeated_controls_equal=4,member_fn=0,sources=sources)
    (ROOT/'results/verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
