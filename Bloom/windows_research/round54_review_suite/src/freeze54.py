import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *
import methods54,mechanism54,online54,audit54,report54,test54
from datetime import datetime,timezone

def main():
    path=ROOT/'plan/freeze.json';assert not path.exists()
    sources=set(ROOT.glob('src/*.py'))|{ROOT/'plan/design-freeze.md',ROOT/'.gitignore'}
    for module in tuple(sys.modules.values()):
        f=getattr(module,'__file__',None)
        if f:
            p=Path(f).resolve()
            if p.suffix=='.py' and p.is_relative_to(BLOOM) and '.condaenv' not in p.parts:sources.add(p)
    inputs=set()
    for ds in ('url','mawi2024_flow','clark','sis',*TCP):inputs.update(paths(ds))
    inputs.update((WR/'round10_fpcache/results/main').glob('rows_*.csv'))
    inputs.update((WR/'round53_index_free_recheck_v4/results').glob('*.json'))
    inputs.update({WR/'round19_gt_fix/results/updated_main_comparisons.csv',WR/'round11_tcp/results/datasets.json',WR/'round17_zerotree/README.md',WR/'round20_zero_guard/README.md',BLOOM/'docs/review_evidence_20261123/gt19_14_cases.csv',BLOOM/'docs/review_evidence_20261123/theory_verification.json'})
    for p in inputs|sources:assert p.is_file(),p
    save(path,dict(created=datetime.now(timezone.utc).isoformat(),sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(sources)},inputs={str(p.relative_to(BLOOM)):sha(p) for p in sorted(inputs)},numpy=np.__version__,python=sys.version,unit_tests=9,RSS_limit_bytes=4*1024**3,disk_reserve_bytes=4*1024**3,max_output_bytes=512*1024**2,predeclared_module_rows=dict(ledgers=434,absolute=6456,zero=186,order=168,online=1071,numerical_cases=6)))
    print('FROZEN',len(sources),'sources',len(inputs),'inputs',flush=True)

if __name__=='__main__':main()
