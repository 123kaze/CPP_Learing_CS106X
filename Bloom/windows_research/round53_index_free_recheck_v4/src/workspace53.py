"""Drop unused host-side per-query region arrays after each frozen builder returns.

q_region is an evaluation workspace, not the region routing metadata charged to
Filter Budget. The current selectors and exact-key replayer read fp_static,
region-level arrays and scalar costs; they do not read q_region. Do not use this
scope for a driver which actually consumes that optional workspace.
"""
import sys
from pathlib import Path
from contextlib import contextmanager
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import E5


@contextmanager
def release_query_regions():
    original=E5.build
    stats=dict(build_calls=0,arrays_released=0,cumulative_array_bytes=0,largest_array_bytes=0,note='Cumulative released allocation volume, not a measurement of peak RSS saving')
    def build(*args,**kwargs):
        c=original(*args,**kwargs);stats['build_calls']+=1
        if c is not None:
            st=c['structure']
            if hasattr(st,'q_region'):
                arr=st.q_region
                assert arr.ndim==1 and arr.dtype.name=='int32' and len(arr)==len(st.fp_static)
                n=int(arr.nbytes);stats['arrays_released']+=1
                stats['cumulative_array_bytes']+=n;stats['largest_array_bytes']=max(stats['largest_array_bytes'],n)
                del st.q_region
        return c
    E5.build=build
    try:yield stats
    finally:E5.build=original
