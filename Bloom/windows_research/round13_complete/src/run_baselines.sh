#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-../../.condaenv/bin/python}
export OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p results/logs
"$PY" - <<'PY'
import hashlib,json
from pathlib import Path
for rel,h in json.loads(Path('plan/baseline-freeze.json').read_text())['sha256'].items():
    assert hashlib.sha256((Path('..')/rel).read_bytes()).hexdigest()==h,rel
print('Baseline freeze verified',flush=True)
PY
for ds in caida caida_flow mawi2020_flow mawi2021_flow mawi2022_flow mawi2024_flow; do
  for cache in index fp64; do
    log="results/logs/baseline_${ds}_${cache}.log"
    echo "START BF $ds $cache"
    if "$PY" -u src/baselines13.py --dataset "$ds" --cache "$cache" > "$log" 2>&1; then
      echo "COMPLETE BF $ds $cache"
    else
      status=$?; echo "FAILED BF $ds $cache exit=$status"; tail -n 25 "$log"; exit "$status"
    fi
  done
done
for method in ra6 grid; do
  log="results/logs/holdout_fp64_${method}.log"
  if "$PY" -u src/holdout_fp64.py "$method" > "$log" 2>&1; then
    echo "COMPLETE supplemental MAWI24 fp64 $method"
  else
    status=$?; echo "FAILED supplemental MAWI24 fp64 $method exit=$status"; tail -n 25 "$log"; exit "$status"
  fi
done
"$PY" - <<'PY'
import json,csv
from pathlib import Path
r=Path('results')
files=sorted((r/'baselines').glob('*/*_completion.json'))
assert len(files)==12
records=[json.loads(p.read_text()) for p in files]
assert all(x['status']=='complete' for x in records)
assert sum(x['cases'] for x in records)==800
for folder in ('holdout_fp64','holdout_grid_fp64'):
    rows=[]
    for f in (r/folder).glob('rows_*.csv'):
        with f.open() as fh:rows.extend(csv.DictReader(fh))
    assert len(rows)==4
(r/'baseline_completion.json').write_text(json.dumps(dict(status='complete',cases=800,bf_rows=1600,supplemental_fp64_rows=8),indent=2)+'\n')
print('BASELINES COMPLETE: 800 cache-specific cases + 8 supplemental fp64 rows',flush=True)
PY
