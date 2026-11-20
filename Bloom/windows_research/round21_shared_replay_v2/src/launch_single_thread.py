"""Pin native thread settings BEFORE importing NumPy or starting frozen workers.

Frozen selector/run files remain unchanged. The prior attempt is preserved under
results/abandoned_late_thread_environment and excluded by the report's main path.
"""
import os
ENV=('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS')
for key in ENV:os.environ[key]='1'
import ctypes
import hashlib
import json
from pathlib import Path
import sys
import numpy
from numba import get_num_threads
ROOT=Path(__file__).resolve().parents[1]
lib=Path(sys.prefix)/'lib/libopenblas.0.dylib'
blas=ctypes.CDLL(str(lib))
f=blas.openblas_get_num_threads;f.restype=ctypes.c_int
assert f()==1 and get_num_threads()==1
record=dict(environment={k:os.environ[k] for k in ENV},openblas_threads=f(),numba_threads=get_num_threads(),
            numpy=numpy.__version__,python=sys.version,
            launcher_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            frozen_runner_sha256=hashlib.sha256((ROOT/'src/run_v2.py').read_bytes()).hexdigest(),
            note='Thread env is inherited by each fresh worker before its NumPy import; prior14-thread attempt excluded.')
p=ROOT/'results/launch_environment.json'
if p.exists():assert json.loads(p.read_text())==record
else:p.write_text(json.dumps(record,indent=2)+'\n')
print('LAUNCH VERIFIED:OpenBLAS=1,Numba=1; inherited environment pinned before all workers',flush=True)
os.execv(sys.executable,[sys.executable,'-u',str(ROOT/'src/run_v2.py')])
