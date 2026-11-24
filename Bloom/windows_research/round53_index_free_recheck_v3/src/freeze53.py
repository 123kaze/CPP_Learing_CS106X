"""One-time pre-data code/input freeze. Refuses to replace an existing freeze."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import worker53,prepare53,cache53,report53,run53,test53
# Differential-test reference and its transitive frozen imports.
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41
from datetime import datetime,timezone


def main():
    out=ROOT/'plan/freeze.json';assert not out.exists()
    sources=set(ROOT.glob('src/*.py'))|{ROOT/'plan/design-freeze.md',ROOT/'.gitignore'}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            p=Path(file).resolve()
            if p.suffix=='.py' and p.is_relative_to(BLOOM) and '.condaenv' not in p.parts:sources.add(p)
    paths=set(p for ds in DATASETS for p in inputs(ds))
    paths.update({ROOT/'results/reuse_provenance.json',WR/'round53_index_free_recheck_v2/plan/freeze.json',WR/'round53_index_free_recheck_v2/results/failure.json'})
    for p in paths:assert p.is_file(),str(p)
    save(out,dict(created_utc=datetime.now(timezone.utc).isoformat(),cases=62,expected_rows=434,sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(sources)},inputs={str(p.relative_to(BLOOM)):sha(p) for p in sorted(paths)},environment=dict(python=sys.version,numpy=np.__version__,cache_array_header_bytes=cache53.ARRAY_HEADER),preflight_tests=12,user_authorized_RSS_limit_bytes=6*1024**3,reused_completed_cases=38,new_cases=24,no_outcome_based_matrix_changes=True))
    print('FROZEN',len(sources),'sources',len(paths),'inputs',flush=True)


if __name__=='__main__':main()
