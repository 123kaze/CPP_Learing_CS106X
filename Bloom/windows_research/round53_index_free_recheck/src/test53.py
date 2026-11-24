import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import *
from cache53 import *
from prepare53 import pack
import unittest


class Tests(unittest.TestCase):
    def test_budget(self):
        for w in (8,9,128):
            c=Cache(w)
            for budget in (0,1,143,144,193,197,673,1024,65536):
                sp=c.layout(budget);a=c.allocate(sp)
                self.assertLessEqual(sp['allocated_bytes'],budget)
                self.assertEqual(sp['slots'],4*sp['buckets'])
                if sp['buckets']:self.assertEqual(sys.getsizeof(a),sp['allocated_bytes'])
    def test_full_key_collision(self):
        for width in (8,9,128):
            c=Cache(width);sp=c.layout(4096);a=c.allocate(sp);h=np.uint64(17)
            x=np.frombuffer(b'a',np.uint8);y=np.frombuffer(b'b',np.uint8)
            insert(a,h,x,sp['buckets'],width)
            self.assertTrue(lookup(a,h,x,sp['buckets'],width))
            before=ah(a);self.assertFalse(lookup(a,h,y,sp['buckets'],width));self.assertEqual(before,ah(a))
    def test_length_not_prefix(self):
        c=Cache(128);sp=c.layout(4096);a=c.allocate(sp)
        insert(a,np.uint64(0),np.frombuffer(b'abc',np.uint8),sp['buckets'],128)
        self.assertFalse(lookup(a,np.uint64(0),np.frombuffer(b'ab',np.uint8),sp['buckets'],128))
    def test_long_bypass(self):
        c=Cache(128);sp=c.layout(4096);a=c.allocate(sp);k=np.zeros(129,np.uint8);before=ah(a)
        self.assertEqual(insert(a,np.uint64(0),k,sp['buckets'],128),0)
        self.assertFalse(lookup(a,np.uint64(0),k,sp['buckets'],128));self.assertEqual(before,ah(a))
    def test_empty_key(self):
        c=Cache(8);sp=c.layout(4096);a=c.allocate(sp);k=np.zeros(0,np.uint8)
        self.assertEqual(insert(a,np.uint64(0),k,sp['buckets'],8),1)
        self.assertTrue(lookup(a,np.uint64(0),k,sp['buckets'],8))
    def test_clock(self):
        c=Cache(8);sp=c.layout(193);self.assertEqual(sp['buckets'],1);a=c.allocate(sp)
        keys=[np.array([i],np.uint8) for i in range(5)]
        for k in keys[:4]:self.assertEqual(insert(a,np.uint64(0),k,1,8),1)
        self.assertEqual(insert(a,np.uint64(0),keys[4],1,8),2)
        self.assertFalse(lookup(a,np.uint64(0),keys[0],1,8))
        self.assertTrue(lookup(a,np.uint64(0),keys[4],1,8))
    def test_index_guard_restores(self):
        old=E5.load
        with no_index():
            for fun in (E5.load,E5.E.load,E5.R.load_setup,C.Setup,C.cache_entry_bits,E5.E.CC.safe_prefix_lengths):
                with self.assertRaisesRegex(AssertionError,'forbids'):fun()
        self.assertIs(E5.load,old)
    def test_layout_scope_restores(self):
        old=E5.K;c=Cache(9)
        with self.assertRaises(ValueError):
            with layout_scope(c):self.assertIs(E5.K,c);raise ValueError()
        self.assertIs(E5.K,old)
    def test_replay_cutoff_strict_and_indices(self):
        blob,offsets=pack([b'M',b'first',b'second']);qi=np.array([2,1],np.int64)
        hashes=np.zeros(2,np.uint64);s=SimpleNamespace(h1q=hashes);c=Cache(8);e=Evaluator(c,s,blob,offsets,qi)
        cand=dict(cache_bytes=c.layout(4096)['allocated_bytes'],structure=SimpleNamespace(fp_static=np.ones(2,np.bool_)))
        stream=np.array([0,1,0,1],np.int64)
        cnt,a=e.evaluate(cand,stream,2);self.assertEqual(cnt[0],2);self.assertEqual(cnt[6],0);self.assertEqual(cnt[1],2)
        cut,_=e.evaluate(cand,stream,1);self.assertEqual(cut[0],2);self.assertEqual(cut[6],1)
        before=ah(a);self.assertEqual(member_hits(a,np.array([0],np.uint64),blob,offsets,np.array([0],np.int64),c.layout(4096)['buckets'],8),0);self.assertEqual(before,ah(a))
    def test_differential_exact41(self):
        sys.path.insert(0,str(WR/'round41_exact_key_budget/src'));import exact41 as old
        rng=np.random.default_rng(5301);keys=[rng.bytes(n) for n in (0,1,8,9,127,128,129,5,8)]
        blob,off=pack(keys);ix=np.arange(len(keys),dtype=np.int64);hs=rng.integers(0,2**64,len(keys),dtype=np.uint64)
        flags=rng.integers(0,2,len(keys)).astype(np.bool_);stream=rng.integers(0,len(keys),500,dtype=np.int64)
        c=Cache(128);sp=c.layout(2000);a=c.allocate(sp);o=old.allocate(old.layout(2000))
        x=replay(stream,hs,blob,off,ix,flags,a,sp['buckets'],128,2**62)
        z=old.replay(stream,hs,blob,off,flags,np.zeros(len(keys),np.bool_),o,sp['buckets'])
        self.assertEqual(int(x[0]),int(z[1]));self.assertEqual(int(x[1]),int(z[3]))
        self.assertTrue(np.array_equal(a[32:],o[32:]))
    def test_tie_break_all_candidates(self):
        blob,off=pack([b'a']);s=SimpleNamespace(h1q=np.array([0],np.uint64));e=Evaluator(Cache(8),s,blob,off,np.array([0],np.int64))
        cands=[dict(trees=t,frac=0.,cache_bytes=0,structure=SimpleNamespace(fp_static=np.array([False]),est_fpr=.1)) for t in (2,1)]
        best,log=e.best(cands,np.array([0,0],np.int64));self.assertEqual(best['trees'],1);self.assertEqual(len(log),2)


if __name__=='__main__':unittest.main(verbosity=2)
