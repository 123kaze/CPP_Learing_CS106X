"""Derive interpretable condition tables from frozen completed Round43 archives."""
from pathlib import Path
import csv,json,statistics,hashlib
BLOOM=Path(__file__).resolve().parents[2];ROOT=Path(__file__).resolve().parent;R=BLOOM/'windows_research/round43_controlled_catalog/results'


def main():
    dest=ROOT/'conditions.json';assert not dest.exists()
    with (R/'main.csv').open() as f:mainrows=list(csv.DictReader(f))
    with (R/'controls.csv').open() as f:controls=list(csv.DictReader(f))
    with (R/'cost_crossovers.csv').open() as f:cost=list(csv.DictReader(f))
    with (R/'cost_projections.csv').open() as f:projections=list(csv.DictReader(f))
    out=dict(synthetic=True,not_production_evidence=True,feature_diagnostics=[],condition_cells=[],fixed_controls=[],selection=[],projections=[])
    for a in (0,6):
        for seed in (4301,4302,4303):
            w=json.loads((R/f'a{a}_s{seed}.json').read_text());meta=w['catalogue']
            assert meta['member_feature_bins']==256 and meta['query_keys_sharing_member_feature']==65536 and meta['feature_support_rule_negative_key_rejects']==0
            out['feature_diagnostics'].append(dict(strength=a,seed=seed,AUC16=w['training']['development_auc_by_trees']['16'],member_bins=256,overlap_fraction=1.,simple_support_rule_rejects=0))
        groups={}
        for r in mainrows:
            if int(r['strength'])==a and r['method'] in ('RA6','Replay'):groups.setdefault((r['seed'],r['association'],r['budget_kib']),{})[r['method']]=float(r['selection_build_s'])+float(r['learning_summary_charged_s'])
        ratios=[x['RA6']/x['Replay'] for x in groups.values()]
        out['selection'].append(dict(strength=a,pairs=len(ratios),RA_faster=sum(x<1 for x in ratios),median_RA_over_Replay=statistics.median(ratios)))
        cc={}
        for r in controls:
            if int(r['strength'])==a:cc.setdefault((r['seed'],r['association'],r['budget_kib']),{})[r['arm']]=int(r['fp'])
        for b in ('h','traffic'):
            pairs=[(r['miss'],r[b]) for r in cc.values()]
            out['fixed_controls'].append(dict(strength=a,baseline=b,wins=sum(x<y for x,y in pairs),ties=sum(x==y for x,y in pairs),losses=sum(x>y for x,y in pairs),median_smoothed_ratio=statistics.median((x+1)/(y+1) for x,y in pairs)))
        for p in (.1,.9):
            for assoc in ('neutral','high_hot','low_hot'):
                for budget in (16,32,64):
                    rows=[r for r in cost if int(r['strength'])==a and float(r['member_target'])==p and r['association']==assoc and int(r['budget_kib'])==budget and r['baseline']=='BF+Cache'];assert len(rows)==3
                    ratios=[float(r['median_paired_time_ratio']) for r in rows]
                    out['condition_cells'].append(dict(strength=a,member_target=p,association=assoc,budget_kib=budget,timing_wins=sum(x<1 for x in ratios),timing_losses=sum(x>1 for x in ratios),median_paired_ratio=statistics.median(ratios),positive_backend_saving_cases=sum(int(r['backend_calls_saved'])>0 for r in rows)))
            for add in (0,5,20,100):
                rr=[r for r in projections if int(r['strength'])==a and float(r['member_target'])==p and r['baseline']=='BF+Cache' and int(r['additional_backend_us'])==add];assert len(rr)==27
                out['projections'].append(dict(strength=a,member_target=p,additional_backend_us=add,cases=27,projected_query_wins=sum(float(r['projected_query_delta_s'])<0 for r in rr),projected_startup_window_wins=sum(float(r['projected_startup_plus_one_window_delta_s'])<0 for r in rr),not_measured_latency=True))
    sources=[R/'main.csv',R/'controls.csv',R/'cost_crossovers.csv',R/'cost_projections.csv']+[R/f'a{a}_s{s}.json' for a in (0,6) for s in (4301,4302,4303)]
    out['sources']={str(p.relative_to(BLOOM)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    out['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    with dest.open('x') as f:json.dump(out,f,indent=2);f.write('\n')
    with (ROOT/'condition_cells.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(out['condition_cells'][0]),lineterminator='\n');w.writeheader();w.writerows(out['condition_cells'])
    print('Verified36 condition cells;6 catalogue support checks;4 fixed-control summaries;16 explicit cost projections. No old output changed.')

if __name__=='__main__':main()
