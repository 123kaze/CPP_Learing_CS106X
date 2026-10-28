"""Pre-register and verify immutable core sources before fresh MAWI outcomes."""
from pathlib import Path
import hashlib,json,sys,datetime
ROOT=Path(__file__).resolve().parents[1]
FILES=['src/runtime.py','src/run_experiments.py','src/compact_cache.py','src/global_lru.py',
       'src/end_to_end.py','src/fetch_mawi.py','plan/experiment-protocol.md',
       'data/mawi2021-source.json','data/mawi2021-download.json']
def digest():
    return {s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in FILES}
dest=ROOT/'plan'/'holdout-freeze.json'
if sys.argv[-1]=='create':
    if dest.exists():raise RuntimeError('Refusing to replace holdout pre-registration')
    obj=dict(frozen_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
             sources=digest(),dataset='mawi2021_flow',budgets_kib=[40,48,64],
             backends=['clock','global_lru'],selection_window_fraction=.25,
             suffix_start='cold_cache',fracs=[0,.01,.02,.05,.1,.2,.3,.4,.6],
             trees=[1,2,4,8,12,16,24,32,48,64,96,128,160,200],
             permitted_repair='Only run-blocking correctness bugs; record amended version and invalidate strict one-shot claim if changed after outcome inspection.')
    dest.write_text(json.dumps(obj,indent=2),encoding='utf-8')
    print('FROZEN',dest)
else:
    amended=ROOT/'plan'/'holdout-freeze-amendment.json'
    obj=json.loads((amended if amended.exists() else dest).read_text(encoding='utf-8'))
    if amended.exists():
        assert obj['original_freeze_sha256']==hashlib.sha256(dest.read_bytes()).hexdigest()
    assert obj['sources']==digest(),'Frozen sources changed'
    print('PASS: frozen core and protocol hashes unchanged')
