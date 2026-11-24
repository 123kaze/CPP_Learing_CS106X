"""Read-only arithmetic/hash audit of full-file diagnosis and training ablation."""
from pathlib import Path
import hashlib,json,time,math
BLOOM=Path(__file__).resolve().parents[2];WR=BLOOM/'windows_research';ROOT=Path(__file__).resolve().parent

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    target=ROOT/'verification.json';assert not target.exists();t=time.perf_counter();checked={}
    for name in ('round50_sis_fullfile_diagnostics','round51_training_stability'):
        r=WR/name;freeze=json.loads((r/'plan/freeze.json').read_text())
        for group in ('sources','inputs'):
            for p,h in freeze[group].items():
                if p not in checked:checked[p]=sha(BLOOM/p)
                assert checked[p]==h,p
    p50=WR/'round50_sis_fullfile_diagnostics';p51=WR/'round51_training_stability';prep=json.loads((p50/'results/preparation.json').read_text());inv=json.loads((WR/'round49_sis_inventory/results/inventory.json').read_text())
    assert prep['members']==inv['members']==2749058 and prep['negative_keys']==inv['negative_keys']==3467 and prep['negative_requests']==inv['retained_404_requests']==63377 and prep['source_sha256']==inv['source_sha256']
    q=json.loads((p50/'results/qualification.json').read_text());assert q['eligible_for_method_comparison'] and not q['method_FP_measured']
    verification=json.loads((p51/'results/verification.json').read_text());gates=[];counts=[]
    for seed in (5001,5002,5003):
        old=json.loads((p50/f'results/seed{seed}.json').read_text());w=json.loads((p51/f'results/seed{seed}.json').read_text());rr={r['recipe']:r for r in w['rows']};assert w['status']=='complete' and set(rr)=={'original','balanced','clip_only','balanced_clip'}
        assert w['learning_sha256']==old['learning_sha256'] and w['tail_sha256']==old['tail_sha256']
        assert abs(rr['original']['development_auc']-old['development_auc16'])<1e-12
        for name,r in rr.items():
            assert not r['score_direction_flipped'] and not r['method_FP_evaluated'] and r['finite_scores']
            assert math.isfinite(r['raw_score_min']) and math.isfinite(r['raw_score_max'])
            if name in ('balanced','balanced_clip'):assert math.isclose(r['positive_weight_mass'],r['negative_weight_mass'],rel_tol=1e-12)
            if name in ('clip_only','balanced_clip'):
                assert r['raw_score_min']>=r['initial_logit']-1.6-1e-5 and r['raw_score_max']<=r['initial_logit']+1.6+1e-5
        passed=rr['balanced_clip']['development_auc']>=.7 and rr['balanced_clip']['development_auc']-rr['original']['development_auc']>=.03
        gates.append(passed);counts.append(dict(seed=seed,negative_train=old['train_negative_keys'],negative_val=old['validation_negative_keys'],learning_queries=old['learning_queries'],tail_queries=old['tail_queries'],retained_negative_request_fraction=(old['learning_queries']+old['tail_queries'])/63377,original_AUC=rr['original']['development_auc'],balanced_clip_AUC=rr['balanced_clip']['development_auc'],gate_passed=passed))
    assert all(gates) and verification['gate_passes']==(sum(gates)>=2) and verification['chosen_recipe_if_gate_passes']=='balanced_clip'
    out=dict(status='verified',source_input_hashes_checked=len(checked),models=12,old_AUC_regressions=3,gate_passed=True,preselected_candidate='balanced_clip',method_FP_measured=False,independent_holdout=False,seed_details=counts,seconds=time.perf_counter()-t,script_sha256=sha(Path(__file__)))
    with target.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    print(json.dumps(out,indent=2))

if __name__=='__main__':main()
