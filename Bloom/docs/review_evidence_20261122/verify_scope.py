"""Read-only evidence arithmetic and prepared feature-schema checks; no experiments rerun."""
from pathlib import Path
from statistics import median
import argparse,csv,hashlib,json,zipfile
BLOOM=Path(__file__).resolve().parents[2]


def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main(output=None):
    sources={}
    def rows(rel):
        p=BLOOM/rel;sources[rel]=sha(p)
        with p.open() as f:return list(csv.DictReader(f))
    def document(rel):
        p=BLOOM/rel;sources[rel]=sha(p);return json.loads(p.read_text())
    def outcome(pairs):
        return dict(pairs=len(pairs),wins=sum(a<b for a,b in pairs),ties=sum(a==b for a,b in pairs),losses=sum(a>b for a,b in pairs),
                    median_smoothed_ratio=median((a+1)/(b+1) for a,b in pairs))
    groups={}
    for r in rows('windows_research/round27_http_real/results/rows.csv'):
        groups.setdefault((r['dataset'],r['seed'],r['budget_kib']),{})[r['method']]=int(r['fp'])
    assert len(groups)==18
    nasa={m:outcome([(r['RA-PLBF-GT19'],r[m]) for r in groups.values()]) for m in ('Replay','RA-global','BF+Cache')}
    nasa['wins_vs_BF_cases']=[dict(dataset=k[0],seed=k[1],budget_kib=k[2],RA=r['RA-PLBF-GT19'],BF=r['BF+Cache']) for k,r in groups.items() if r['RA-PLBF-GT19']<r['BF+Cache']]
    r37=rows('windows_research/round37_clarknet_controls/results/main.csv')
    med={str(b):{m:median(int(r['fp']) for r in r37 if int(r['budget_kib'])==b and r['method']==m) for m in ('Gama','Replay','RA-global','RA-PLBF-GT19','BF+Cache')} for b in (8,16,32)}
    assert med['32']['RA-PLBF-GT19']==137>med['32']['Replay']==134
    speed=[]
    for seed in ('3601','3602','3603'):
        for budget in ('8','16','32'):
            rr={r['method']:r for r in r37 if r['seed']==seed and r['budget_kib']==budget}
            speed.append(float(rr['RA-PLBF-GT19']['build_and_select_s'])/float(rr['Replay']['build_and_select_s']))
    hold=[r for r in rows('windows_research/round19_gt_fix/results/updated_main_comparisons.csv') if r['dataset']=='mawi2024_flow']
    assert len(hold)==8
    hold=[{k:r[k] for k in ('cache','budget_kib','cohort','repaired_ra_fp','replay_fp','bf_cache_fp','provenance')} for r in hold]
    features=[];missing=[]
    import numpy as np
    for ds in ('caida_flow','mawi2020_flow','mawi2021_flow','mawi2022_flow','mawi2024_flow'):
        folder=BLOOM/'windows_research/round2_backlog/cache'/ds;p=folder/'data.npz';model=folder/'model200.txt'
        if not p.exists() or not model.exists():missing.append(ds);continue
        with np.load(p,allow_pickle=False) as f:names=f['features'].tolist()
        with zipfile.ZipFile(p) as z,z.open('X.npy') as f:
            version=np.lib.format.read_magic(f)
            shape,_,dtype=np.lib.format.read_array_header_1_0(f) if version==(1,0) else np.lib.format.read_array_header_2_0(f)
        found={}
        with model.open() as f:
            for line in f:
                if line.startswith(('max_feature_idx=','feature_names=')):
                    k,v=line.strip().split('=',1);found[k]=v
                if len(found)==2:break
        assert names==['src','dst'] and shape[1]==2 and found=={'max_feature_idx':'1','feature_names':'src dst'}
        for file in (p,model):sources[str(file.relative_to(BLOOM))]=sha(file)
        features.append(dict(dataset=ds,features=names,matrix_shape=list(shape),dtype=str(dtype),model=found))
    for rel in ('windows_research/round6_bucket/plan/freeze.json','windows_research/round6_bucket/plan/holdout-predeclare.json',
                'windows_research/round37_clarknet_controls/results/verification.json','windows_research/round38_horizon_sensitivity/results/verification.json',
                'windows_research/round39_deployment_accounting/results/verification.json','windows_research/round40_fingerprint_assumptions/results/verification.json'):
        document(rel)
    result=dict(status='verified' if not missing else 'partial_prepared_features_unavailable',scope='read-only arithmetic and metadata, not independent third-party rerun',
                NASA=nasa,ClarkNet_median_FP=med,ClarkNet_selection_cost=dict(RA_slower_cases=sum(x>1 for x in speed),cases=9,median_ratio=median(speed),minimum=min(speed),maximum=max(speed)),
                MAWI24_posthoc_fingerprint_results=hold,verified_flow_features=features,unavailable_prepared_features=missing,sources=sources)
    text=json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    if output:
        with Path(output).open('x') as f:f.write(text)
    print(json.dumps(dict(status=result['status'],NASA=nasa,flow_features_verified=len(features),RA_slower_small_workload_cases=sum(x>1 for x in speed)),ensure_ascii=False,indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);a=parser.parse_args();main(a.output)
