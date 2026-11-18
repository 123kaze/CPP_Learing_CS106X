"""Reuse the exact round17 case matrix; results never select this round's winner."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round17_zerotree/src'))
from common17 import TCP,MID,FRESH,DATASETS,cases,digest,ah,save
METHODS=('RA6-ZGate','RA6-GT19','BF+ReplayCache')
