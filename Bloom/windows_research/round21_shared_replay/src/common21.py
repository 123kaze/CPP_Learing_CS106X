from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round17_zerotree/src'))
from common17 import TCP,MID,DATASETS,cases,digest,ah,save
TIMING_REPS=3


def timed_case(ds,kib,name,seed):
    return (ds in TCP and kib==TCP[ds][1]) or (ds in MID and kib==MID[ds] and name=='zipf1.0-全部' and seed==0)
