#!/usr/bin/env bash
# Serial, failure-propagating runner. Wrap this script with caffeinate on macOS.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=${PYTHON:-../../.condaenv/bin/python}
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
mkdir -p results/logs
"$PY" - <<'PY'
import hashlib,json
from pathlib import Path
r=Path.cwd()
f=json.loads((r/'plan/freeze.json').read_text())
for rel,want in f['sha256'].items():
    p=r.parent/rel
    if hashlib.sha256(p.read_bytes()).hexdigest()!=want:
        raise SystemExit(f'Frozen source changed: {rel}')
print('Freeze verified',flush=True)
PY
for ds in url cod shalla caida_tcp_flow mawi2020_tcp_flow mawi2021_tcp_flow mawi2022_tcp_flow; do
  for cache in index fp64; do
    log="results/logs/${ds}_${cache}.log"
    echo "START $ds $cache"
    if "$PY" -u src/run12.py --dataset "$ds" --cache "$cache" > "$log" 2>&1; then
      echo "COMPLETE $ds $cache"
    else
      status=$?
      echo "FAILED $ds $cache exit=$status"
      tail -n 30 "$log"
      exit "$status"
    fi
  done
done
"$PY" - <<'PY'
import json
from pathlib import Path
r=Path('results/main')
files=sorted(r.glob('*/*_completion.json'))
assert len(files)==14, len(files)
rows=[json.loads(f.read_text()) for f in files]
assert all(x['status']=='complete' for x in rows)
assert sum(x['cases'] for x in rows)==1532
out=dict(status='complete',cache_specific_cases=1532,rows=sum(x['rows'] for x in rows),jobs=14)
Path('results/completion.json').write_text(json.dumps(out,indent=2)+'\n')
print('ALL COMPLETE: 766 cases x 2 cache formats, 3064 result rows',flush=True)
PY
