"""Artificial backend service-cost adapter. No model/cache/label logic lives here."""
import os
for v in ('OMP_NUM_THREADS','NUMBA_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','VECLIB_MAXIMUM_THREADS'):os.environ[v]='1'
from pathlib import Path
import sys,time
ROOT=Path(__file__).resolve().parents[1];WR=ROOT.parent;BLOOM=WR.parent
sys.path.insert(0,str(WR/'round31_sqlite_online/src'))
from online31 import online_run,Online,E5,J,B,K,sha,ah,save,np
from worker31 import original_reference,SETTINGS
DELAYS_US=(0,5,10,25,50,100)
METHODS=('RA6','BF+Cache')


class BackendCostCursor:
    def __init__(self,cursor,extra_us,clock=time.perf_counter_ns):
        if extra_us<0:raise ValueError('Negative artificial cost')
        self.cursor=cursor;self.extra_ns=int(round(extra_us*1000));self.clock=clock
        self.calls=0;self.busy_wait_ns=0;self.min_wait_ns=None;self.max_wait_ns=0

    def execute(self,query,parameters):
        self.cursor.execute(query,parameters)
        return self

    def fetchone(self):
        # The actual SQL result is obtained first. The frozen driver cannot insert before return.
        row=self.cursor.fetchone();self.calls+=1
        if self.extra_ns:
            clock=self.clock;start=clock();now=start;deadline=start+self.extra_ns
            while now<deadline:now=clock()
            elapsed=now-start;self.busy_wait_ns+=elapsed
            self.min_wait_ns=elapsed if self.min_wait_ns is None else min(self.min_wait_ns,elapsed)
            self.max_wait_ns=max(self.max_wait_ns,elapsed)
        return row

    def close(self):self.cursor.close()

    def stats(self):
        return dict(actual_backend_responses=self.calls,requested_extra_ns_per_call=self.extra_ns,
                    requested_extra_ns_total=self.calls*self.extra_ns,observed_busy_wait_ns_total=self.busy_wait_ns,
                    observed_min_wait_ns=self.min_wait_ns,observed_max_wait_ns=self.max_wait_ns,
                    observed_mean_wait_ns=self.busy_wait_ns/self.calls if self.calls else None)
