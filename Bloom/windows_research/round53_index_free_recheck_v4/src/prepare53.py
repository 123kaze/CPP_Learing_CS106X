"""Unmodified frozen key preparation, writing only this round's new cache directory."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common53
import frozen53 as _loader
_original=_loader.load('prepare53')
_loader.export(_original,globals())

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('dataset',choices=DATASETS);a=p.parse_args()
    try:prepare(a.dataset)
    except Exception as e:save(ROOT/f'results/raw_{a.dataset}.failure.json',dict(status='failed',error_type=type(e).__name__,error=str(e)[:500]));raise
