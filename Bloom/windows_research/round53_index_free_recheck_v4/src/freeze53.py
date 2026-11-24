"""Freeze new adapters plus every imported frozen implementation before method evaluation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
import worker53,prepare53,cache53,report53,test53,workspace53
sys.path.insert(0,str(WR/'round41_exact_key_budget/src'))
import exact41  # Include differential-test dependencies in the source freeze.
from datetime import datetime,timezone


def main():
    out=ROOT/'plan/freeze.json';assert not out.exists()
    preflight=json.loads((ROOT/'results/preflight_tests_process.json').read_text())
    assert preflight['status']=='complete' and preflight['exit_code']==0
    sources=set(ROOT.glob('src/*.py'))|{ROOT/'plan/design-freeze.md',ROOT/'.gitignore'}
    for module in tuple(sys.modules.values()):
        file=getattr(module,'__file__',None)
        if file:
            p=Path(file).resolve()
            if p.suffix=='.py' and p.is_relative_to(BLOOM) and '.condaenv' not in p.parts:sources.add(p)
    paths=set(p for ds in DATASETS for p in inputs(ds))
    paths.add(ROOT/'results/reuse_provenance.json')
    for name in ('round53_index_free_recheck','round53_index_free_recheck_v2','round53_index_free_recheck_v3'):
        paths.update({WR/name/'plan/freeze.json',WR/name/'results/failure.json'})
    for p in sources|paths:assert p.is_file(),str(p)
    save(out,dict(created_utc=datetime.now(timezone.utc).isoformat(),cases=62,rows=434,reused_cases=38,new_cases=24,sources={str(p.relative_to(BLOOM)):sha(p) for p in sorted(sources)},inputs={str(p.relative_to(BLOOM)):sha(p) for p in sorted(paths)},environment=dict(python=sys.version,numpy=np.__version__,cache_array_header_bytes=cache53.ARRAY_HEADER),preflight_tests=14,user_authorized_RSS_limit_bytes=6*1024**3,user_authorized_workspace_optimization=True,no_outcome_based_matrix_changes=True,change='Release unused q_region after frozen E5.build; preserve original return fields otherwise'))
    print('FROZEN',len(sources),'sources',len(paths),'inputs',flush=True)


if __name__=='__main__':main()
