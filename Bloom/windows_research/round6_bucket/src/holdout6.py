"""MAWI 2024 holdout plumbing: register the dataset, then run a script unchanged.

usage: holdout.py prepare
       holdout.py run <script.py> [args...]   (any runner that imports round-2 engine)
The dataset is registered exactly like mawi2022_flow in round2_backlog/src/prepare_datasets.py.
"""
import runpy
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
R2 = HERE.parents[1] / 'round2_backlog'
sys.path.insert(0, str(R2 / 'src'))
import prepare_datasets as D  # noqa: E402  (sets the round-2 cache and registry)

D.C.DATASETS['mawi2024_flow'] = dict(raw=R2 / 'data', member_train=.5, neg_cuts=(.1, .2))
D.R.C.DATASETS['mawi2024_flow'] = D.C.DATASETS['mawi2024_flow']

if __name__ == '__main__':
    if sys.argv[1] == 'prepare':
        src = HERE.parent / 'data' / 'mawi2024.csv'
        dst = R2 / 'data' / 'mawi2024.csv'
        if not dst.exists():
            shutil.copyfile(src, dst)
        D.prepare('mawi2024_flow')
    else:
        script = sys.argv[2]
        sys.argv = [script] + sys.argv[3:]
        sys.path.insert(0, str(Path(script).resolve().parent))
        runpy.run_path(script, run_name='__main__')
