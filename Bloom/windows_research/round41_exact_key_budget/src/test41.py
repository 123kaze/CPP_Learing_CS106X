import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import exact41 as E
import unittest
np=E.np

def key(x):return np.frombuffer(x,np.uint8)

class Tests(unittest.TestCase):
    def test_layout_and_headers(self):
        for budget in (0,1,128,672,673,1024,8192,16384):
            spec=E.layout(budget);d=E.allocate(spec)
            self.assertLessEqual(spec['allocated_bytes'],budget)
            if spec['buckets']:
                self.assertEqual(sys.getsizeof(d),spec['allocated_bytes'])
                self.assertGreater(E.ARRAY_HEADER+E.HEAD+(spec['buckets']+1)*E.BUCKET_BYTES,budget)
    def test_forced_alias_and_full_equality(self):
        s=E.layout(1024);d=E.allocate(s);h=np.uint64(42)
        self.assertEqual(E.insert(d,h,key(b'negative'),s['buckets']),1)
        self.assertTrue(E.lookup(d,h,key(b'negative'),s['buckets']))
        self.assertFalse(E.lookup(d,h,key(b'member!!'),s['buckets']))
        self.assertFalse(E.lookup(d,h,key(b'negativeX'),s['buckets']))
        self.assertFalse(E.lookup(d,h,key(b'negativE'),s['buckets']))
    def test_long_and_empty_keys(self):
        s=E.layout(1024);d=E.allocate(s);h=np.uint64(0)
        self.assertEqual(E.insert(d,h,key(b''),s['buckets']),1)
        self.assertTrue(E.lookup(d,h,key(b''),s['buckets']))
        self.assertEqual(E.insert(d,h,key(b'x'*128),s['buckets']),1)
        self.assertFalse(E.lookup(d,h,key(b'x'*128+b'a'),s['buckets']))
        before=d.copy();self.assertEqual(E.insert(d,h,key(b'x'*128+b'b'),s['buckets']),0)
        self.assertTrue(np.array_equal(before,d))
    def test_clock_eviction(self):
        s=E.layout(1024);d=E.allocate(s);h=np.uint64(1)
        for j in range(4):self.assertEqual(E.insert(d,h,key(bytes([j])),1),1)
        self.assertEqual(E.insert(d,h,key(b'z'),1),2)
        self.assertFalse(E.lookup(d,h,key(b'\x00'),1))
        self.assertTrue(E.lookup(d,h,key(b'z'),1))
    def test_alias_mixed_replay(self):
        blob,off=E.pack([b'absent',b'present']);hs=np.array([0,0],np.uint64)
        stream=np.array([0,1,0,1],np.int64);member=np.array([False,True]);flags=np.ones(2,np.bool_)
        s=E.layout(1024);d=E.allocate(s)
        cnt=E.replay(stream,hs,blob,off,flags,member,d,s['buckets'])
        self.assertEqual(cnt.tolist()[:5],[3,1,2,1,0])
        self.assertEqual(E.member_hits(d,hs,blob,off,np.array([1],np.int64),s['buckets']),0)
    def test_binding_restored_on_error(self):
        self.assertIs(E.E5.K,E.K)
        with self.assertRaisesRegex(RuntimeError,'intentional'):
            with E.exact_layout():
                self.assertIs(E.E5.K,E)
                raise RuntimeError('intentional')
        self.assertIs(E.E5.K,E.K)
    def test_scalar_replay_reference(self):
        # Independent one-bucket CLOCK implementation over raw Python bytes.
        keys=[b'',b'ab',b'ac',b'd',b'e',b'f',b'a'*129,b'member']
        rng=np.random.default_rng(4101);stream=rng.integers(0,len(keys),300,dtype=np.int64)
        member=np.arange(len(keys))==7;flags=np.ones(len(keys),np.bool_);flags[4]=False
        slots=[None]*4;refs=[False]*4;hand=0;expected=np.zeros(8,np.int64)
        for x in stream:
            k=keys[x];hit=next((i for i,v in enumerate(slots) if v==k),None)
            if hit is not None:refs[hit]=True;expected[3]+=1;expected[4]+=int(member[x]);continue
            if not flags[x]:expected[4]+=int(member[x]);continue
            expected[0]+=1
            if member[x]:expected[2]+=1;continue
            expected[1]+=1
            if len(k)>128:expected[7]+=1;continue
            free=next((i for i,v in enumerate(slots) if v is None),None)
            if free is None:
                for _ in range(8):
                    if not refs[hand]:break
                    refs[hand]=False;hand=(hand+1)%4
                free=hand;hand=(hand+1)%4;expected[6]+=1
            slots[free]=k;refs[free]=True;expected[5]+=1
        blob,off=E.pack(keys);s=E.layout(1024);d=E.allocate(s)
        got=E.replay(stream,np.zeros(len(keys),np.uint64),blob,off,flags,member,d,1)
        np.testing.assert_array_equal(got,expected)

if __name__=='__main__':unittest.main()
