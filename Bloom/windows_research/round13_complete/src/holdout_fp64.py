"""Post-hoc frozen fp64 RA6/Replay on MAWI24, not a new independent holdout."""
import argparse
from pathlib import Path
import sys
from baselines13 import ROOT,WR,register,BUDGETS


def run(method):
    register()
    sys.path.insert(0,str(WR/'round10_fpcache/src'))
    if method=='ra6':
        import run10
        run10.ROOT=ROOT
        run10.run('mawi2024_flow',BUDGETS['mawi2024_flow'],10000000,1,'holdout_fp64')
    else:
        import grid10
        import cache_fp
        grid10.ROOT=ROOT
        grid10.E5.K=cache_fp
        grid10.run('mawi2024_flow',BUDGETS['mawi2024_flow'],1,'LearnGrid-fp64','holdout_grid_fp64')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('method',choices=('ra6','grid'));run(p.parse_args().method)
