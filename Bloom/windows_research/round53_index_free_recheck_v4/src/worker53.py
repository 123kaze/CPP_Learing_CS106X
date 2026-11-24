"""Frozen v3 experiment, scoped to release only its unused per-query region workspace."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common53,cache53
from common53 import ROOT,DATASETS,BUDGETS,save
from workspace53 import release_query_regions
import frozen53 as _loader
_original=_loader.load('worker53')
assert _original.ROOT==ROOT


def run(ds,kib,pilot=False):
    with release_query_regions() as stats:
        _original.run(ds,kib,pilot)
    name=('pilot_' if pilot else '')+f'{ds}_{kib}'
    assert stats['arrays_released']>0
    save(ROOT/f'results/{name}_workspace.json',stats)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=DATASETS);p.add_argument('kib',type=int);p.add_argument('--pilot',action='store_true');a=p.parse_args()
    assert a.kib in BUDGETS[a.dataset]
    try:run(a.dataset,a.kib,a.pilot)
    except Exception as e:save(ROOT/f'results/{"pilot_" if a.pilot else ""}{a.dataset}_{a.kib}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:500]));raise
