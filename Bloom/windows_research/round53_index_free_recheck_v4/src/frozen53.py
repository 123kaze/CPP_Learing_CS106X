"""Import explicitly named frozen v3 modules without editing or copying their sources."""
import importlib.util
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT.parent/'round53_index_free_recheck_v3/src'
ALLOWED={'common53','cache53','prepare53','worker53','report53','test53'}


def load(name):
    assert name in ALLOWED
    alias='_frozen_round53v3_'+name
    if alias in sys.modules:return sys.modules[alias]
    path=SOURCE/(name+'.py')
    spec=importlib.util.spec_from_file_location(alias,path)
    module=importlib.util.module_from_spec(spec);sys.modules[alias]=module
    spec.loader.exec_module(module)
    # Frozen modules may add their own script folder. New adapters take precedence.
    sys.path.insert(0,str(ROOT/'src'))
    return module


def export(module,namespace):
    namespace.update({k:v for k,v in vars(module).items() if not k.startswith('_')})
