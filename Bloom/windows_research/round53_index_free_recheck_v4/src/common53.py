"""Frozen common helpers, with outputs/prepared inputs rooted in this new round only."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import frozen53 as _loader
_original=_loader.load('common53')
_original.ROOT=_loader.ROOT
_loader.export(_original,globals())
