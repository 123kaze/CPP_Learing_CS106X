import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from account39 import calls,project,required_index_bytes
from worker39 import replay,CACHES,E5,np,W
from types import SimpleNamespace
import unittest


class Tests(unittest.TestCase):
    def test_learning_cost_is_incremental_not_all_requests(self):
        a=calls(1000,3000,200,300,100)
        self.assertEqual(a['extra_learning_backend_calls'],800)
        self.assertEqual(a['tail_backend_calls_saved'],200)
        self.assertEqual(a['net_backend_calls_saved_after_one_window'],-600)
        self.assertAlmostEqual(a['backend_only_break_even_negative_queries'],12000)
        # Add the same members to both phases: they cancel, not become an RA-only expense.
        ra=9000+1000+27000+100;baseline=9000+200+27000+300
        self.assertEqual(ra-baseline,600)
        shared=calls(1000,3000,1000,300,100,shared_learning=True)
        self.assertEqual(shared['extra_learning_backend_calls'],0)
        self.assertEqual(shared['net_backend_calls_saved_after_one_window'],200)

    def test_break_even_and_nonpositive_benefit(self):
        a=calls(1000,3000,200,300,100)
        r=project(a,1.,10.,0.,0.)
        self.assertEqual(r['status'],'positive_slope')
        n=r['break_even_total_queries'];b=r['benefit_us_per_total_query']
        self.assertLessEqual(r['incremental_startup_and_learning_s']-n*b/1e6,1e-12)
        self.assertGreater(r['incremental_startup_and_learning_s']-(n-1)*b/1e6,-1e-12)
        slow=project(a,1.,10.,.1,.9)
        self.assertIsNone(slow['break_even_total_queries'])
        self.assertLess(slow['benefit_us_per_total_query'],0.)
        worse=calls(1000,3000,200,100,200)
        self.assertIsNone(project(worse,0.,10.,0.,0.)['break_even_total_queries'])

    def test_resource_boundary_and_invalid_inputs(self):
        self.assertEqual(required_index_bytes('index',100,3000000,112),24000112)
        self.assertEqual(required_index_bytes('index',0,3000000,112),0)
        self.assertEqual(required_index_bytes('fp64',100,3000000,112),0)
        with self.assertRaises(ValueError):calls(100,100,101,1,1)
        with self.assertRaises(ValueError):project(calls(100,100,10,20,10),0.,1.,0.,1.)

    def test_distinct_key_state_can_exceed_raw_trace(self):
        trace=np.arange(1024,dtype=np.int64);summary=W.summarize19(trace)
        self.assertEqual(summary.state_bytes,2*trace.nbytes)
        self.assertEqual(summary.keys.nbytes+summary.counts.nbytes+summary.rate.nbytes,3*trace.nbytes)

    def test_cache_state_really_carries_between_phases(self):
        s=SimpleNamespace(h1m=E5.C.splitmix64(np.array([10,11],np.uint64)),h1q=E5.C.splitmix64(np.array([20,21],np.uint64)))
        safe=E5.E.CC.safe_prefix_lengths(np.sort(s.h1m),s.h1q)
        seq=np.array([0,1,0,1],np.int64)
        for mode,cache in CACHES.items():
            spec=cache.layout(512);c=dict(cache_bytes=spec['allocated_bytes'],structure=SimpleNamespace(fp_static=np.ones(2,np.bool_)))
            first,state=replay(c,seq,s,safe if mode=='index' else None,mode)
            old=state
            second,state=replay(c,seq,s,safe if mode=='index' else None,mode,state)
            self.assertIs(state,old)
            self.assertGreater(first['fp'],0)
            self.assertEqual(second['fp'],0)
            cold,_=replay(c,seq,s,safe if mode=='index' else None,mode)
            self.assertEqual(cold['fp'],first['fp'])
            self.assertEqual(second['member_cache_hits'],0)


if __name__=='__main__':unittest.main()
