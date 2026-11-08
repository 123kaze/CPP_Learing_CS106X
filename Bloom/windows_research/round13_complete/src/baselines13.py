"""Extend round12's frozen no-model runner to the missing datasets; do not edit it."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
WR=ROOT.parent
sys.path.insert(0,str(WR/'round12_nomodel/src'))
import run12

BUDGETS={'caida':(128,256,1024,2048),'caida_flow':(16,24,32,256),
         'mawi2020_flow':(16,24,32,128),'mawi2021_flow':(16,24,32,128),
         'mawi2022_flow':(16,24,32,128),'mawi2024_flow':(16,24,32,128)}


def register():
    sys.path.insert(0,str(WR/'round6_bucket/src'))
    import holdout6  # registration only; no download or prepare


def run(a):
    register()
    run12.ROOT=ROOT
    run12.all_budgets=lambda ds:BUDGETS[ds]
    manifest=dict(budgets=BUDGETS,source_sha256=run12.digest_file(Path(__file__)),
                  runner_sha256=run12.digest_file(Path(run12.__file__)),
                  note='Same round12 BF/cache protocol; MAWI24 is a post-hoc added baseline.')
    manifest=json.loads(json.dumps(manifest))
    p=ROOT/'results'/a.tag/'wrapper.json'
    if p.exists() and json.loads(p.read_text())!=manifest:
        raise RuntimeError('Wrapper changed; use a new tag.')
    run12.save_json(p,manifest)
    run12.run(a)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--dataset',choices=tuple(BUDGETS),required=True)
    p.add_argument('--cache',choices=('index','fp64'),required=True)
    p.add_argument('--budgets')
    p.add_argument('--queries',type=int,default=10000000)
    p.add_argument('--seeds',type=int,default=5)
    p.add_argument('--tag',default='baselines')
    a=p.parse_args()
    if a.queries<4 or a.seeds<1:p.error('queries>=4 and seeds>=1 required')
    run(a)
