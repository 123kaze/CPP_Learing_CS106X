import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import catalog43 as C
import online43 as O
import unittest,tempfile
np=C.np

class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.s,cls.X,cls.h,cls.meta=C.catalogue(2,4399,1024,256,1024)
    def test_deterministic_disjoint_raw_domain(self):
        s,X,h,meta=C.catalogue(2,4399,1024,256,1024)
        np.testing.assert_array_equal(s.ids,self.s.ids)
        self.assertEqual(len(np.unique(s.ids)),len(s.ids));self.assertEqual(len(np.unique(h)),len(h))
        self.assertTrue(np.all(s.y.astype(int)+s.split['neg_train']+s.split['neg_val']+s.split['neg_test']==1))
        raw=[int(x).to_bytes(8,'little') for x in s.ids]
        np.testing.assert_array_equal([int.from_bytes(k,'little') for k in raw],s.ids)
    def test_query_features_do_not_read_labels(self):
        expected=((self.s.ids>>np.uint64(56)).astype(np.float32)/np.float32(255)).reshape(-1,1)
        np.testing.assert_array_equal(expected,self.X)
        self.assertGreater(self.meta['query_keys_sharing_member_feature'],0)
    def test_region_mass_held_fixed(self):
        previous=None
        for arm in C.ASSOCIATIONS:
            p,r,e,m=C.probabilities(self.s,arm,4399)
            np.testing.assert_allclose(np.bincount(r,weights=p,minlength=5),m)
            if previous is not None:np.testing.assert_array_equal(m,previous)
            previous=m
        self.assertTrue((C.probabilities(self.s,'high_hot',4399)[2]==C.probabilities(self.s,'low_hot',4399)[2][::-1]).all())
    def test_seeded_stream_and_split(self):
        a,b,m=C.stream(self.s,'neutral',4399,4000);c,d,n=C.stream(self.s,'neutral',4399,4000)
        self.assertEqual((len(a),len(b)),(1000,3000));self.assertEqual(m,n)
        np.testing.assert_array_equal(a,c);np.testing.assert_array_equal(b,d)
    def test_hash_raw_uint64_equivalence(self):
        expected=C.E5.C.splitmix64(self.s.ids^np.uint64(C.E5.C.H1_SALT)^np.uint64(4399))
        np.testing.assert_array_equal([O.hash_key(x,4399) for x in self.s.ids],expected)
    def test_cache_stores_all64bits(self):
        f=C.F;sp=f.layout(1024);data=f.allocate(sp);a=np.uint64(0x1234567800000001);b=a^np.uint64(1)
        f.insert(data,a,sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4,sp['handbits'])
        self.assertTrue(f.lookup(data,a,sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4))
        self.assertFalse(f.lookup(data,b,sp['buckets'],64,sp['Q'],sp['ob'],sp['slot_bits'],4))
        self.assertEqual(sys.getsizeof(data),sp['allocated_bytes'])
    def test_binding_exception_restored(self):
        with self.assertRaises(RuntimeError):
            with C.exact64():self.assertIs(C.E5.K,C.F);raise RuntimeError('intentional fixture')
        self.assertIs(C.E5.K,C.K_ORIGINAL)
    def test_real_sql_matches_reference(self):
        s,X,h=self.s,self.X,self.h;scores,_=C.train(s,X,4399)
        keys=[int(x).to_bytes(8,'little') for x in s.ids];_,tail,_=C.stream(s,'neutral',4399,4000)
        with C.exact64():
            learned=C.E5.build(s,scores,1,8,.1);bf=C.B.build(s,8,.1,C.F)
            with tempfile.TemporaryDirectory() as tmp:
                con,_=O.database(Path(tmp)/'kv.sqlite',keys,s.y)
                try:
                    rows,_=O.measure({'RA6':learned,'Replay':learned,'BF+Cache':bf},s,scores,h,keys,tail,4399,con.cursor(),n=40,reps=1)
                    self.assertEqual(len(rows),8);self.assertTrue(all(r['member_fn']==0 and r['reference_equal'] for r in rows))
                finally:con.close()

if __name__=='__main__':unittest.main()
