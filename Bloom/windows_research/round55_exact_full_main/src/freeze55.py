"""Create the exact case manifest and hash every source/input before new performance results."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common55 import *
import worker55,report55,test55
from datetime import datetime,timezone


def main():
    target=ROOT/'plan/freeze.json';assert not target.exists() and not (ROOT/'plan/cases.json').exists()
    settings=[];refs=set();keys=set()
    for p in sorted((WR/'round6_bucket/results/main').glob('rows_*.csv')):
        rr=[r for r in readcsv(p) if r['method']=='RA6'];assert rr
        ds=rr[0]['dataset'];kib=int(rr[0]['budget_kib']);gfile=WR/f'round5_dp/results/rows_{ds}_{kib}.csv'
        g={(r['workload'],int(r['seed'])):r for r in readcsv(gfile) if r['method']=='Gama'};cases=[]
        for r in rr:
            key=(ds,kib,r['workload'],int(r['seed']));assert key not in keys;keys.add(key);old=g[key[2:]]
            cases.append(dict(dataset=ds,budget_kib=kib,workload=key[2],seed=key[3],historical_Gama_fp=int(old['fp_tail']),historical_Gama_trees=int(old['trees']),cohort='main'))
        settings.append(dict(dataset=ds,budget_kib=kib,cases=cases));refs.update({p,gfile})
    assert len(keys)==1146 and sum(k[2]==E5.PROBE for k in keys)==70 and len(settings)==30
    for kib in (16,24,32,128):
        p=WR/f'round6_bucket/results/holdout/round5_methods/rows_mawi2024_flow_{kib}.csv';g=next(r for r in readcsv(p) if r['method']=='Gama');refs.add(p)
        case=dict(dataset='mawi2024_flow',budget_kib=kib,workload='真实轨迹',seed=0,historical_Gama_fp=int(g['fp_tail']),historical_Gama_trees=int(g['trees']),cohort='previously_used_MAWI24')
        settings.append(dict(dataset='mawi2024_flow',budget_kib=kib,cases=[case]))
    save(ROOT/'plan/cases.json',dict(main_cases=1146,nonprobe=1076,probe=70,additional_MAWI24=4,settings=settings))
    refs.add(ROOT/'plan/cases.json');refs.update((WR/'round53_index_free_recheck_v4/results').glob('*.json'))
    for ds in {s['dataset'] for s in settings}:refs.update(input_paths(ds))
    sources=set(ROOT.glob('src/*.py'))|{ROOT/'plan/design-freeze.md',ROOT/'.gitignore'}
    for m in tuple(sys.modules.values()):
        name=getattr(m,'__file__',None)
        if name:
            p=Path(name).resolve()
            if p.suffix=='.py' and p.is_relative_to(BLOOM) and '.condaenv' not in p.parts:sources.add(p)
    for p in refs|sources:assert p.is_file(),p
    save(target,dict(created_utc=datetime.now(timezone.utc).isoformat(),sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(sources)},inputs={str(p.relative_to(BLOOM)):sha(p) for p in sorted(refs)},main_cases=1146,additional_cases=4,RSS_limit_bytes=4*1024**3,disk_reserve_bytes=4*1024**3,formal_deadline_s=28800,preflight='test55.py must pass before this freeze stage; no real results examined'))
    print('FROZEN',len(sources),'sources',len(refs),'inputs; 1146+4 exact cases',flush=True)

if __name__=='__main__':main()
