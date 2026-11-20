from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round21_shared_replay/src'))
from common21 import DATASETS,TCP,MID,cases,digest,ah,save
METHODS=('RA6','ZGate-serial','ZGate-shared','Grid-serial','Grid-shared')
REPS=3
