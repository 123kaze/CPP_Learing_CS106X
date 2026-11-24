"""Unmodified frozen exact-key cache implementation."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common53
import frozen53 as _loader
_original=_loader.load('cache53')
_loader.export(_original,globals())
