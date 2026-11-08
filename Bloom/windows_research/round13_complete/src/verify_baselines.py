"""Independently verify full baseline coverage and hashes, with stdlib only.

Raw result rows are read, not trusted through a completion counter or precomputed summary.
--inputs is for the experiment host; omit on a data-free clone.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median
from collections import Counter,defaultdict

ROOT=Path(__file__).resolve().parents[1]
WR=ROOT.parent
NEW={'caida':(128,256,1024,2048),'caida_flow':(16,24,32,256),
     'mawi2020_flow':(16,24,32,128),'mawi2021_flow':(16,24,32,128),
     'mawi2022_flow':(16,24,32,128),'mawi2024_flow':(16,24,32,128)}
PROBE='探测重放10%'


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def expected(ds):
    if ds!='caida':return {('真实轨迹',0)}
    names=[f'{w}-{pool}' for pool in ('1万','10万','100万','全部')
           for w in ('uniform','zipf0.8','zipf1.0','zipf1.2')]+['每key一次','全新对抗',PROBE]
    return {(w,s) for w in names for s in range(5)}


def main(with_inputs):
    files={}
    def read(p):
        text=p.read_text(encoding='utf-8')
        files[str(p.relative_to(WR))]=digest(p)
        return text
    for rel,want in json.loads(read(ROOT/'plan/baseline-freeze.json'))['sha256'].items():
        assert digest(WR/rel)==want,rel
    results={};raw_count=0;extra=0
    for mode in ('index','fp64'):
        suffix='' if mode=='index' else '-fp64'
        for ds,budgets in NEW.items():
            folder=ROOT/'results/baselines'/mode
            meta_path=folder/f'{ds}_inputs.json'
            meta=json.loads(read(meta_path));done=json.loads(read(folder/f'{ds}_completion.json'))
            assert digest(meta_path)==done['inputs_sha256']
            assert meta['dataset']==ds and meta['cache']==mode and meta['budgets']==list(budgets)
            assert meta['queries']==10000000 and meta['seeds']==([0,1,2,3,4] if ds=='caida' else [0])
            assert done['status']=='complete' and done['cases']==len(budgets)*len(expected(ds))
            if with_inputs:
                for rel,want in {**meta['inputs'],**meta['sources']}.items():
                    assert digest(WR.parent/rel)==want,rel
            for kib in budgets:
                p=folder/f'rows_{ds}_{kib}.csv'
                by=defaultdict(dict)
                for row in csv.DictReader(read(p).splitlines()):
                    method=row['method'];key=(row['workload'],int(row['seed']))
                    assert method in ('BF'+suffix,'BF+ReplayCache'+suffix)
                    assert method not in by[key],(p,key,method)
                    assert row['dataset']==ds and int(row['budget_kib'])==kib and row['cache_mode']==mode
                    assert int(row['trees'])==int(row['model_bytes'])==0
                    f,n=int(row['fp_tail']),int(row['tail_len'])
                    assert 0<=f<=n and math.isclose(float(row['fpr_tail']),f/n,rel_tol=1e-12)
                    used=sum(int(row[k]) for k in ('bf_bytes','metadata_bytes','overhead_bytes','cache_alloc_bytes'))
                    assert used==int(row['total_bytes'])<=kib*1024
                    assert int(row['metadata_bytes'])==32
                    by[key][method]=row;raw_count+=1
                assert by.keys()==expected(ds),(p,len(by))
                for key,rows in by.items():
                    assert set(rows)=={'BF'+suffix,'BF+ReplayCache'+suffix}
                    p,b=rows['BF'+suffix],rows['BF+ReplayCache'+suffix]
                    assert p['base_stream_sha256']==b['base_stream_sha256'] and p['tail_len']==b['tail_len']
                    if key[0]!=PROBE:assert p['tail_stream_sha256']==b['tail_stream_sha256']
                    results[ds,kib,*key,mode]=rows
    assert raw_count==1600
    for (ds,kib,w,seed,mode),rows in results.items():
        if mode!='index':continue
        a=rows['BF'];b=results[ds,kib,w,seed,'fp64']['BF-fp64']
        assert a['fp_tail']==b['fp_tail'] and a['base_stream_sha256']==b['base_stream_sha256']
    for folder,method in (('holdout_fp64','RA6-fp64'),('holdout_grid_fp64','LearnGrid-fp64')):
        for kib in NEW['mawi2024_flow']:
            p=ROOT/'results'/folder/f'rows_mawi2024_flow_{kib}.csv'
            rows=list(csv.DictReader(read(p).splitlines()))
            assert len(rows)==1 and rows[0]['method']==method
            assert int(rows[0]['budget_kib'])==kib and rows[0]['seed']=='0'
            if method=='RA6-fp64':assert int(rows[0]['member_hits_final'])==0
            extra+=1
    assert extra==8
    allrows=list(csv.DictReader(read(ROOT/'results/combined_baseline_rows.csv').splitlines()))
    keys={(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),r['cache']) for r in allrows}
    assert len(allrows)==len(keys)==2332
    summary=json.loads(read(ROOT/'results/baseline_summary.json'))
    for mode in ('index','fp64'):
        rows=[r for r in allrows if r['cache']==mode and r['cohort']=='main' and r['workload']!=PROBE]
        assert len(rows)==1076
        eligible=[r for r in rows if r['included']=='True']
        assert len(eligible)==748
        ratio=lambda r:(int(r['ra_fp'])+1)/(int(r['bfcache_fp'])+1)
        s=summary[f'{mode}/all']
        assert median(map(ratio,eligible))==s['median']
        wins=sum(int(r['ra_fp'])<int(r['bfcache_fp']) for r in eligible)
        losses=[r for r in eligible if int(r['ra_fp'])>int(r['bfcache_fp'])]
        assert wins==s['wins'] and len(losses)==s['losses']
        print(mode,'eligible',len(eligible),'wins',wins,'losses',len(losses),
              'loss_groups',dict(Counter((r['dataset'],r['workload']) for r in losses)))
    # Persist hashes of the archived records actually checked, excluding this self-referential output.
    p=ROOT/'results/baseline_verification.json'
    p.write_text(json.dumps(dict(status='verified',new_bf_rows=raw_count,extra_holdout_rows=extra,
                                combined_cases=len(allrows),checked_raw_inputs=with_inputs,
                                sources=files),indent=2)+'\n')
    print('PASS: complete baseline coverage, byte budgets, paired streams, hashes and summary arithmetic.')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--inputs',action='store_true');main(p.parse_args().inputs)
