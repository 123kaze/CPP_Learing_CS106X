import unittest
from types import SimpleNamespace
import numpy as np
import shared21 as S


def candidate(fp,cache_bytes):
    return dict(cache_bytes=cache_bytes,structure=SimpleNamespace(fp_static=np.asarray(fp,np.bool_)))


class SharedReplayTests(unittest.TestCase):
    def compare(self,hashes,members,stream,flags,budgets,mode,safe_override=None):
        setup=SimpleNamespace(h1q=hashes)
        safe=S.E5.E.CC.safe_prefix_lengths(np.sort(members),hashes) if safe_override is None else safe_override
        candidates=[candidate(f,b) for f,b in zip(flags,budgets)]
        keys,counts=np.unique(stream,return_counts=True)
        expected,states=S.serial_full(candidates,stream,setup,safe,mode)
        actual=S.replay(candidates,stream,setup,safe,keys,counts,mode)
        self.assertTrue(np.array_equal(actual['counters'],expected),(mode,actual['counters'],expected))
        for a,b in zip(actual['states'],states):self.assertEqual(a.tobytes(),b.tobytes())
        return actual

    def test_cross_prefix_non_fp_changes_eviction(self):
        heads=[0x10,0x30,0x50,0x70,0x90,0xb0]
        h=np.array([(x<<56)+1 for x in heads]+[(0x30<<56)+2],np.uint64)
        members=np.array([((x+1)<<56) for x in heads],np.uint64)
        stream=np.array([0,1,2,3,4,6,5,1],np.int64)
        flags=np.array([True]*6+[False])
        out=self.compare(h,members,stream,[flags],[176],'index')
        self.assertEqual(int(out['counters'][0,0]),6)
        self.assertGreater(out['additional_routed_keys'][0],0)
        safe=S.E5.E.CC.safe_prefix_lengths(np.sort(members),h)
        naive=S.C5.simulate(stream[flags[stream]],h,safe,flags,176)
        self.assertEqual(naive['fp'],7)

    def test_fp64_alias_even_for_non_fp_key(self):
        h=np.array([100,100,200,300,400,500,600],np.uint64)
        flags=np.array([True,False,True,True,True,True,True])
        stream=np.array([0,2,3,4,5,1,6,0],np.int64)
        out=self.compare(h,np.array([2**63],np.uint64),stream,[flags],[256],'fp64')
        self.assertGreater(out['additional_routed_keys'][0],0)

    def test_random_candidates_both_formats(self):
        rng=np.random.default_rng(2121)
        h=rng.integers(0,2**64-1,200,dtype=np.uint64)
        members=rng.integers(0,2**64-1,100,dtype=np.uint64)
        flags=[rng.random(len(h))<p for p in (0.,.01,.1,.5,1.,.3)]
        stream=rng.integers(0,len(h),5000,dtype=np.int64)
        for mode in ('index','fp64'):self.compare(h,members,stream,flags,[0,256,512,1024,4096,200],mode)

    def test_multiple_mask_words(self):
        rng=np.random.default_rng(21)
        h=rng.integers(0,2**63,40,dtype=np.uint64);members=np.array([2**63],np.uint64)
        flags=[rng.random(40)<.2 for _ in range(180)]
        stream=rng.integers(0,40,500,dtype=np.int64)
        for mode in ('index','fp64'):self.compare(h,members,stream,flags,[256]*180,mode)

    def test_prefix_clipped_to_actual_bucket(self):
        h=np.array([0x1000000000000001,0x3000000000000002,0x6000000000000003,0x7f00000000000004],np.uint64)
        members=np.array([0x8000000000000000],np.uint64)
        stream=np.array([0,1,2,3,0,1],np.int64)
        self.compare(h,members,stream,[[True,False,False,False]],[1024],'index')

    def test_high_hash_endpoints(self):
        h=np.array([0xffffffffffffffff,0xfffffffffffffffe,0xfffe000000000000,1,2],np.uint64)
        members=np.array([1<<63],np.uint64)
        self.compare(h,members,np.array([0,1,2,0,4],np.int64),[[True,False,True,False,True]],[257],'index')

    def test_unsafe_prefix_bypasses(self):
        h=np.array([5,6,7,8],np.uint64);stream=np.tile(np.arange(4,dtype=np.int64),20)
        self.compare(h,np.array([1],np.uint64),stream,[[True]*4],[256],'index',np.array([41,65,40,1],np.uint8))

    def test_zero_cache_exact_weighted_count(self):
        h=np.arange(10,dtype=np.uint64);stream=np.tile(np.arange(10,dtype=np.int64),3)
        for mode in ('index','fp64'):
            out=self.compare(h,np.array([100],np.uint64),stream,[[True]*10],[0],mode)
            self.assertEqual(out['visits'][0],0)
            self.assertEqual(out['counters'][0,0],30)


if __name__=='__main__':unittest.main()
