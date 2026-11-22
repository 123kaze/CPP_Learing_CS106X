import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import online42 as O
from worker42 import bf_build,fixture
from types import SimpleNamespace
import unittest,tempfile,sqlite3
np=O.np


class Tests(unittest.TestCase):
    def setup_case(self,mode='exact',alias=False):
        keys=[b'absent',b'present',b'x'*129]
        hs=np.full(3,42,np.uint64) if alias else np.array([O.raw_hash(k,4102) for k in keys],np.uint64)
        s=SimpleNamespace(name='toy_4102',h1m=hs[1:2].copy(),h1q=hs[[0,2]].copy())
        c=bf_build(s,4096,.5,O.E if mode=='exact' else O.K)
        flt=O.Filter(c,s,{},mode,np.sort(s.h1m))
        return keys,hs,s,c,flt
    def test_raw_hash_equivalence(self):
        import hashlib
        keys=[b'',b'abc',b'a'*1000,b'\x00\xff']
        ids=np.array([int.from_bytes(hashlib.sha256(k).digest()[:8],'little') for k in keys],np.uint64)
        expected=O.E5.C.splitmix64(ids^np.uint64(O.E5.C.H1_SALT)^np.uint64(4102))
        np.testing.assert_array_equal([O.raw_hash(k,4102) for k in keys],expected)
    def test_actual_sql_forced_hash_alias(self):
        keys,hs,s,c,flt=self.setup_case(alias=True);original=O.raw_hash
        with tempfile.TemporaryDirectory() as tmp:
            con,_=fixture(Path(tmp)/'kv.sqlite',keys,[False,True,False])
            try:
                O.raw_hash=lambda key,seed:np.uint64(42)
                req=np.array([0,1,0,1],np.int64);mask=np.zeros(4,np.uint8);found=np.zeros(4,np.uint8)
                got=O.online(con.cursor(),keys,req,flt,mask,found,collect=True)
                self.assertEqual((got['backend_calls'],got['fp'],got['members_found'],got['cache_hits']),(3,1,2,1))
                np.testing.assert_array_equal(found,[0,1,0,1]);self.assertEqual(got['negative_count_sum'],2)
                self.assertEqual(got['negative_distinct'],1)
            finally:O.raw_hash=original;con.close()
    def test_sql_exception_does_not_admit(self):
        keys,hs,s,c,flt=self.setup_case(alias=True);original=O.raw_hash;before=flt.data.copy()
        class Broken:
            def execute(self,*args):raise sqlite3.OperationalError('synthetic failure')
        try:
            O.raw_hash=lambda key,seed:np.uint64(42)
            with self.assertRaises(sqlite3.OperationalError):O.online(Broken(),keys,np.array([0]),flt,np.zeros(1,np.uint8),np.zeros(1,np.uint8))
            np.testing.assert_array_equal(flt.data,before)
        finally:O.raw_hash=original
    def test_prefix_complete_alias_bypass(self):
        keys,hs,s,c,flt=self.setup_case('prefix',True)
        self.assertEqual(flt.absent(np.uint64(42),np.frombuffer(keys[0],np.uint8)),0)
        self.assertFalse(O.K.lookup(flt.data,np.uint64(42),flt.spec['buckets'],40,flt.spec['Q'],flt.spec['ob'],flt.spec['slot_bits'],4))
    def test_direct_index_is_not_positive_cache(self):
        keys,hs,s,c,_=self.setup_case();flt=O.Filter(None,s,{},'direct',np.sort(s.h1m))
        with tempfile.TemporaryDirectory() as tmp:
            con,_=fixture(Path(tmp)/'kv.sqlite',keys,[False,True,False])
            try:
                req=np.array([0,1,2,1]);m=np.zeros(4,np.uint8);f=np.zeros(4,np.uint8)
                got=O.online(con.cursor(),keys,req,flt,m,f)
                self.assertEqual(got['backend_calls'],2);self.assertEqual(got['members_found'],2)
                self.assertEqual(got['fp'],0)
            finally:con.close()
    def test_learned_raw_path_and_reference(self):
        keys=[(('/kind'+str(i%7)+'/resource_'+str(i)+'.html') if i%3==0 else ('/item/'+str(i)+'?q='+str(i%11))).encode() for i in range(200)]
        y=np.arange(200)%3==0;neg=np.flatnonzero(~y);val=np.zeros(200,np.bool_);val[neg[:20]]=True;test=(~y)&~val
        hs=np.array([O.raw_hash(k,4199) for k in keys],np.uint64);X=np.asarray([O.lexical(k) for k in keys],np.float32)
        s=SimpleNamespace(name='synthetic_4199',y=y,split={'neg_val':val,'neg_test':test},h1m=hs[y],h1q=hs[test])
        model=O.W.lgb.train(dict(objective='binary',num_leaves=7,min_data_in_leaf=5,num_threads=1,verbose=-1,seed=4199),O.W.lgb.Dataset(X,label=y),num_boost_round=1)
        scores={1:model.predict(X,raw_score=True,num_threads=1)};O.E5.R._MODEL_ARRAYS[s.name,1]=O.W.model_arrays(model,1)
        blob,off=O.E.pack(keys);req=np.tile(np.flatnonzero(y|test),2).astype(np.int64);index=np.sort(s.h1m)
        with tempfile.TemporaryDirectory() as tmp:
            con,_=fixture(Path(tmp)/'kv.sqlite',keys,y)
            try:
                for mode in ('exact','prefix'):
                    if mode=='exact':
                        with O.E.exact_layout():c=O.E5.build(s,scores,1,8,.2)
                    else:c=O.E5.build(s,scores,1,8,.2)
                    flt=O.Filter(c,s,scores,mode,index);flags=np.ones(200,np.bool_);flags[test]=c['structure'].fp_static
                    d=O.E.allocate(flt.spec) if mode=='exact' else O.K.allocate(flt.spec);p=flt.spec
                    rm,rf=O.reference(req,hs,blob,off,flags,y,d,1 if mode=='exact' else 2,p['buckets'],p.get('Q',32),p.get('ob',0),p.get('slot_bits',0),p.get('handbits',0),index)
                    m=np.zeros(len(req),np.uint8);f=np.zeros_like(m);got=O.online(con.cursor(),keys,req,flt,m,f)
                    np.testing.assert_array_equal(m,rm);np.testing.assert_array_equal(f,rf);np.testing.assert_array_equal(flt.data,d)
                    self.assertEqual(got['members_found'],int(y[req].sum()))
            finally:con.close()
    def test_no_filter_has_no_hash_work(self):
        keys=[b'a',b'b'];orig=O.raw_hash
        with tempfile.TemporaryDirectory() as tmp:
            con,_=fixture(Path(tmp)/'kv.sqlite',keys,[True,False])
            try:
                def forbidden(*args):raise AssertionError('unnecessary hash')
                O.raw_hash=forbidden
                got=O.online(con.cursor(),keys,np.array([0,1]),None,np.zeros(2,np.uint8),np.zeros(2,np.uint8))
                self.assertEqual(got['backend_calls'],2)
            finally:O.raw_hash=orig;con.close()

if __name__=='__main__':unittest.main()
