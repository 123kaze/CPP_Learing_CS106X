"""Integration checks on the prepared smoke artifacts; not performance evidence."""
import unittest
from common16 import *
import numpy as np
import rocksdict as Rocks
from native16 import *


class NativeChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.requests=np.load(ROOT/'inputs/requests.npz')
        cls.ids=cls.requests['ids'];cls.X=cls.requests['X'];cls.nm=int(cls.requests['members'])
        cls.opts,cls.cache=db_options(CACHES['pressure'])
        cls.db=Rocks.Rdict(str(ROOT/'db/url'),cls.opts,column_families={'default':cls.opts},access_type=Rocks.AccessType.read_only())

    @classmethod
    def tearDownClass(cls):cls.db.close()

    def load_native(self,method):
        p=ROOT/f'inputs/smoke_filters/zipf_rep0_{method}.npz'
        meta=json.loads(p.with_suffix('.json').read_text())
        with np.load(p) as f:a={k:f[k].copy() for k in KEYS}
        return make_native(a,method=='BFCache',meta['cache_bytes'])

    def test_hash_matches_frozen(self):
        n=self.load_native('BFCache')
        for i in (0,self.nm,self.nm+100,len(self.ids)-1):
            n.probe(self.ids[i],self.X[i])
            self.assertEqual(int(n.last_hash),int(C.splitmix64(self.ids[i:i+1]^np.uint64(C.H1_SALT))[0]))

    def test_backend_none_precedes_cache_insertion(self):
        n=self.load_native('BFCache');i=None
        for j in range(self.nm,min(self.nm+10000,len(self.ids))):
            if n.probe(self.ids[j],self.X[j])==1:i=j;break
        self.assertIsNotNone(i)
        before=n.state.copy()
        self.assertEqual(n.probe(self.ids[i],self.X[i]),1)
        self.assertTrue(np.array_equal(before,n.state),'probe inserted without feedback')
        self.assertIsNone(self.db.get(key_bytes(self.ids[i])))
        self.assertIn(n.feedback(),(1,2))
        self.assertEqual(n.probe(self.ids[i],self.X[i]),2)
        self.assertTrue((probe_all(n,self.ids[:self.nm],self.X[:self.nm])==1).all())

    def test_positive_value_does_not_update_cache(self):
        for method in ('BFCache','RA6','Replay'):
            n=self.load_native(method);before=n.state.copy()
            self.assertEqual(n.probe(self.ids[0],self.X[0]),1)
            value=self.db.get(key_bytes(self.ids[0]))
            self.assertEqual(value[:8],key_bytes(self.ids[0]))
            self.assertTrue(np.array_equal(before,n.state))

    def test_real_db_contains_all_members_and_no_negative_sample(self):
        for i in range(0,self.nm,101):self.assertIsNotNone(self.db.get(key_bytes(self.ids[i])))
        for i in range(self.nm,len(self.ids),101):self.assertIsNone(self.db.get(key_bytes(self.ids[i])))


if __name__=='__main__':unittest.main()
