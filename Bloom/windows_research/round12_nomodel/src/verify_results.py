"""Verify committed result completeness, memory accounting and report arithmetic (stdlib only).

With --inputs, also re-hash the large prepared input caches on the experiment host.
"""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
from statistics import median

ROOT=Path(__file__).resolve().parents[1]


def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(1<<20),b''):
            h.update(chunk)
    return h.hexdigest()


def main(check_inputs):
    out=ROOT/'results'
    f=json.loads((ROOT/'plan/freeze.json').read_text())
    for relative,want in f['sha256'].items():
        assert digest(ROOT.parent/relative)==want,relative
    seen=set();case_rows={};count=0
    for mode in ('index','fp64'):
        for p in sorted((out/'main'/mode).glob('rows_*.csv')):
            with p.open(encoding='utf-8') as fh:
                for r in csv.DictReader(fh):
                    key=(r['dataset'],int(r['budget_kib']),r['workload'],int(r['seed']),mode,r['method'])
                    assert key not in seen,key
                    seen.add(key);count+=1
                    assert r['cache_mode']==mode
                    assert int(r['trees'])==int(r['model_bytes'])==0
                    assert 0<=int(r['fp_tail'])<=int(r['tail_len'])
                    assert math.isclose(float(r['fpr_tail']),int(r['fp_tail'])/int(r['tail_len']),rel_tol=1e-12)
                    used=sum(int(r[k]) for k in ('bf_bytes','metadata_bytes','overhead_bytes','cache_alloc_bytes'))
                    assert used==int(r['total_bytes'])<=int(r['budget_kib'])*1024
                    assert int(r['metadata_bytes'])==32 and int(r['k'])>=1
                    case_rows.setdefault(key[:4],{}).setdefault(mode,{})[r['method']]=r
    assert count==3064 and len(case_rows)==766,(count,len(case_rows))
    for key,modes in case_rows.items():
        assert set(modes)=={'index','fp64'}
        originals=[]
        for mode,methods in modes.items():
            suffix='-fp64' if mode=='fp64' else ''
            assert set(methods)=={'BF'+suffix,'BF+ReplayCache'+suffix},key
            p,b=methods['BF'+suffix],methods['BF+ReplayCache'+suffix]
            assert p['base_stream_sha256']==b['base_stream_sha256']
            assert p['learning_queries']==b['learning_queries']
            assert int(p['cache_alloc_bytes'])==0
            if key[2]!='探测重放10%':assert p['tail_stream_sha256']==b['tail_stream_sha256']
            originals.append(p)
        assert originals[0]['base_stream_sha256']==originals[1]['base_stream_sha256']
        assert originals[0]['fp_tail']==originals[1]['fp_tail']
    completions=sorted((out/'main').glob('*/*_completion.json'))
    assert len(completions)==14
    checked_hashes={}
    for p in completions:
        d=json.loads(p.read_text());assert d['status']=='complete'
        inputs=p.with_name(p.name.replace('_completion.json','_inputs.json'))
        assert digest(inputs)==d['inputs_sha256']
        if check_inputs:
            meta=json.loads(inputs.read_text())
            for relative,want in {**meta['inputs'],**meta['sources']}.items():
                target=ROOT.parents[1]/relative
                if target not in checked_hashes:checked_hashes[target]=digest(target)
                assert checked_hashes[target]==want,relative
    with (out/'row_comparisons.csv').open(encoding='utf-8') as f:
        comparisons=list(csv.DictReader(f))
    assert len(comparisons)==1532
    s=json.loads((out/'summary.json').read_text())
    for mode in ('index','fp64'):
        selected=[r for r in comparisons if r['cache']==mode and r['is_tcp']=='False' and
                  r['workload']!='探测重放10%' and r['included']=='True']
        assert len(selected)==465
        ratios=[(int(r['ra_fp'])+1)/(int(r['bf_cache_fp'])+1) for r in selected]
        assert median(ratios)==s[mode+'/合计']['median']
        losses=[r for r in selected if int(r['ra_fp'])>int(r['bf_cache_fp'])]
        assert len(losses)==20
        assert all((r['dataset'],r['workload'])==('shalla','全新对抗') for r in losses)
        tcp=[r for r in comparisons if r['cache']==mode and r['is_tcp']=='True']
        assert len(tcp)==16
        assert median((int(r['ra_fp'])+1)/(int(r['bf_cache_fp'])+1) for r in tcp)==s['tcp/'+mode]['median']
    print(f'PASS: {count} rows, 766 paired cases, 14 successful jobs; accounting, streams, summaries and freeze verified.')
    if check_inputs:print(f'PASS: {len(checked_hashes)} unique input/source files re-hashed.')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--inputs',action='store_true')
    main(p.parse_args().inputs)
