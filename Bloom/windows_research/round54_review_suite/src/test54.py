import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from shared54 import *
from methods54 import permute
from mechanism54 import direct_mass,simplex_grid,reference as numref
from online54 import url_features,identity_features,Backend,online,reference,ticks,spin_to

class Tests(unittest.TestCase):
    def test_width32_exact(self):
        cache=Exact(32);sp=cache.layout(4096);data=cache.allocate(sp);a=np.arange(32,dtype=np.uint8);b=a.copy();b[-1]=33
        K53.insert(data,np.uint64(1),a,sp['buckets'],32);self.assertTrue(K53.lookup(data,np.uint64(1),a,sp['buckets'],32));self.assertFalse(K53.lookup(data,np.uint64(1),b,sp['buckets'],32))
    def test_permutation_counts(self):
        x=np.array([2,3,2,0,3,2],np.int64)
        for mode in ('original','shuffled','bursty','cyclic'):
            y=permute(x,mode);self.assertTrue(np.array_equal(np.bincount(x),np.bincount(y)))
        self.assertEqual(permute(x,'cyclic').tolist(),[0,2,3,2,3,2])
    def test_features_and_identity(self):
        keys=['http://www.a3.com/a-b?q=2','é域名.com/ABC.pdf','1.2.3.4','//a@b/%20','https://A.CO/www//x','a..x/']
        old=C.url_features(pd.Series(keys)).to_numpy(np.float32)
        expected=pd.util.hash_pandas_object(pd.Series(keys),index=False).to_numpy(np.uint64)
        for i,key in enumerate(keys):
            raw=key.encode('utf-8');self.assertTrue(np.array_equal(url_features(raw),old[i]))
            h,_=identity_features(raw,'url',0,False);self.assertEqual(h,C.splitmix64(expected[i:i+1]^np.uint64(C.H1_SALT))[0])
    def test_direct_capacity_and_saturation(self):
        seg=np.array([0,1]);lam=np.array([.1,.05]);w=np.array([20.,40.]);G=np.zeros(2);e=np.ones(2);H=100
        m,T,sat,occ=direct_mass(e,seg,lam,w,G,H,8,2)
        self.assertFalse(sat);self.assertAlmostEqual(occ,8,places=10)
        m,T,sat,occ=direct_mass(e,seg,lam,w,G,H,1000,2);self.assertTrue(sat);self.assertEqual(T,100000)
    def test_simplex_and_reference(self):
        grid=list(simplex_grid(3,12));self.assertEqual(len(grid),91);self.assertTrue(all(sum(g)==12 for g in grid))
        n=np.array([100.,100.]);bits=500.;base=RA.ra4.eps_closed(np.ones(2),n,bits)
        r=numref(n,bits,lambda e:float(e@np.array([10.,100.])),base,base)
        self.assertLessEqual(r['best_observed_feasible'],r['objective3']);self.assertFalse(r['global_optimum_certified'])
    def test_scope_restoration(self):
        old=E5.K;build=E5.build
        with self.assertRaises(RuntimeError):
            with scope(Exact(8)):raise RuntimeError('fixture')
        self.assertIs(E5.K,old);self.assertIs(E5.build,build)
    def test_reference_full_keys(self):
        blob=np.frombuffer(b'ab',np.uint8).copy();off=np.array([0,1,2],np.int64);hashes=np.zeros(2,np.uint64);requests=np.array([1,1,0,1],np.int64);flags=np.ones(2,np.bool_);y=np.array([True,False]);c=Exact(8);sp=c.layout(4096);state=c.allocate(sp)
        a,f=reference(requests,hashes,blob,off,flags,y,state,sp['buckets'],8)
        self.assertEqual(a.tolist(),[1,0,1,0]);self.assertEqual(f.tolist(),[0,0,1,0])
    def test_service_real_feedback(self):
        b=Backend({b'a'},3);self.assertEqual(len(b.lookup(b'a')),32);self.assertIsNone(b.lookup(b'b'))
        r,m,f=online([b'a',b'b',b'a'],None,b);self.assertEqual(r['calls'],3);self.assertEqual(r['fp'],1);self.assertEqual(f.tolist(),[1,0,1])
    def test_GT_order_invariance(self):
        x=np.array([1,1,1,2,2,3],np.int64);a=summarize19(x);b=summarize19(x[::-1]);self.assertEqual(ah(a.rate),ah(b.rate))

if __name__=='__main__':unittest.main(verbosity=2)
