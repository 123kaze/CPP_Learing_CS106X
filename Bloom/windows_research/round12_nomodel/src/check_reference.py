"""One representative archived RA6 case per synthetic dataset; separate process per dataset."""
import argparse
import csv
import json
from pathlib import Path
import sys
import numpy as np
import baseline as B

sys.path.insert(0,str(B.WR/'round6_bucket/src'))
import ra6

ROOT=Path(__file__).resolve().parents[1]
BUDGET={'cod':256,'url':64,'shalla':1024}


def run(ds):
    kib=BUDGET[ds];workload='zipf1.0-全部';seed=0
    new,safe_new,_=B.load_setup(ds,'index')
    original,scores,safe=B.E5.load(ds)
    for field in ('h1m','h1q','q_score'):
        assert np.array_equal(getattr(new,field),getattr(original,field)),field
    assert np.array_equal(safe_new,safe)
    spec=dict(B.E5.workload_specs(len(original.h1q)))[workload]
    stream=B.E5.base_stream(original,workload,spec,seed)
    assert np.array_equal(stream,B.E5.base_stream(new,workload,spec,seed))
    n=len(stream)//4
    lm=ra6.RA.ra4.summarize(stream[:n],True)
    c,info=ra6.select6(original,scores,lm,kib,len(stream)-n)
    result=B.E5.evaluate(c,stream[n:],original,safe)
    p=B.WR/'round6_bucket/results/main'/f'rows_{ds}_{kib}.csv'
    with p.open(encoding='utf-8') as f:
        archive=[r for r in csv.DictReader(f) if (r['method'],r['workload'],int(r['seed']))==('RA6',workload,seed)]
    assert len(archive)==1
    ref=archive[0]
    assert result['fp']==int(ref['fp_tail'])
    assert c['trees']==int(ref['trees'])
    assert c['cache_bytes']==int(ref['cache_alloc_bytes'])
    r=dict(dataset=ds,budget_kib=kib,workload=workload,seed=seed,fp=result['fp'],trees=c['trees'],
           cache_bytes=c['cache_bytes'],matches_archived_ra6=True,loader_and_stream_match=True)
    (ROOT/'results'/f'reference_check_{ds}.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=tuple(BUDGET));run(p.parse_args().dataset)
