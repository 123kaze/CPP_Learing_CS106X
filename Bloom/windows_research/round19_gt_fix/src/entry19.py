"""Scoped, reversible runtime hook. Frozen files are never edited.

Use in a fresh worker. This intentionally has no generic runpy launcher: frozen
CLI drivers may overwrite old output roots, skip cached records or assert against
old tables. The round19 adapter owns output and old/new assertions explicitly.
"""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):
    os.environ[v]='1'
import hashlib
import json
import sys
from pathlib import Path
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round4_ra_plbf/src'))
import ra4
from summarize19 import summarize19
ORIGINAL_SUMMARIZE=ra4.summarize


def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''):h.update(b)
    return h.hexdigest()


def save(p,obj):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)+'\n');tmp.replace(p)


def ah(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()


def check_frozen():
    p=ROOT/'plan/freeze.json'
    if p.exists():
        for rel,h in json.loads(p.read_text())['sources'].items():assert digest(BLOOM/rel)==h,rel


@contextmanager
def patched():
    check_frozen()
    before=digest(Path(ra4.__file__))
    assert ra4.summarize is ORIGINAL_SUMMARIZE,'Unexpected or nested summary patch'
    ra4.summarize=summarize19
    try:
        yield
    finally:
        ra4.summarize=ORIGINAL_SUMMARIZE
        assert digest(Path(ra4.__file__))==before,'Frozen counter file changed'
        check_frozen()
