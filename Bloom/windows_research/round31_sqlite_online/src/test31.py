import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from online31 import *
import unittest
import sqlite3
from types import SimpleNamespace
import lightgbm as lgb
from end_to_end import model_arrays


class PoisonSpace:
    @property
    def member(self):raise AssertionError('Online path tried to read labels')


def fixture():
    space=PoisonSpace();space.h=E5.C.splitmix64(np.array([1,2],np.uint64));space.sorted_m=np.sort(space.h[:1]);space.X=np.empty((0,0),np.float32)
    data=B.allocate(1,4096,K.layout(512)['allocated_bytes']);data[B.HEAD_WORDS:]=np.uint64(0xffffffffffffffff) # deliberately PASS-like fixture
    c=dict(cache_bytes=K.layout(512)['allocated_bytes'],structure=SimpleNamespace(data=data))
    return space,Online(c,space)


class Tests(unittest.TestCase):
    def test_probe_does_not_admit(self):
        s,f=fixture();before=f.data.copy()
        self.assertEqual(f.probe(1),1);self.assertEqual(f.probe(1),1);np.testing.assert_array_equal(before,f.data)

    def test_only_actual_SQL_absence_admits(self):
        s,f=fixture();db=sqlite3.connect(':memory:');db.execute('create table kv(key integer primary key,value blob)');db.execute('insert into kv values (1,?)',(b'value',))
        keys=np.array([1,2],np.int64);requests=np.array([1,1,0,0,1],np.int64);mask=np.zeros(len(requests),np.uint8)
        out=online_run(db.cursor(),'select value from kv where key=?',keys,requests,f,mask)
        self.assertEqual(out['backend_calls'],3);self.assertEqual(out['fp'],1);self.assertEqual(out['members_found'],2);self.assertEqual(out['cache_hits'],2)
        np.testing.assert_array_equal(mask,[1,0,1,1,0]);self.assertEqual(f.probe(0),1)
        # Opposite labels would prevent admission, but cannot reach the online driver.
        fake_labels=np.array([False,True]);self.assertTrue(fake_labels[1]);self.assertEqual(f.probe(1),2);db.close()

    def test_independent_BF_reference_state(self):
        s,f=fixture();stream=np.array([1,0,1,1,0,1],np.int64);p=f.spec;state=K.allocate(p)
        cnt,mask=reference_bf(stream,s.h,np.array([True,False]),f.c['structure'].data,state,s.sorted_m,p['buckets'],p['Q'],p['ob'],p['slot_bits'],p['handbits'])
        db=sqlite3.connect(':memory:');db.execute('create table kv(key integer primary key,value blob)');db.execute('insert into kv values(1,?)',(b'v',));actual=np.zeros(len(stream),np.uint8)
        r=online_run(db.cursor(),'select value from kv where key=?',np.array([1,2],np.int64),stream,f,actual)
        np.testing.assert_array_equal(actual,mask);np.testing.assert_array_equal(f.data,state)
        self.assertEqual([r['backend_calls'],r['fp'],r['members_found'],r['cache_hits']],cnt.tolist());db.close()

    def test_compact_learned_route_matches_frozen(self):
        rng=np.random.default_rng(31);N=300;ids=np.arange(N,dtype=np.uint64);y=ids<150;X=rng.normal(size=(N,2)).astype(np.float32);X[y,0]+=1
        split=dict(member_train=y&(ids<100),neg_train=(ids>=150)&(ids<180),neg_val=(ids>=180)&(ids<210),neg_test=ids>=210)
        h=E5.C.splitmix64(ids);s=SimpleNamespace(name='unit_sqlite31',ids=ids,y=y,split=split,h1m=h[y],h1q=h[split['neg_test']])
        train=split['member_train']|split['neg_train'];model=lgb.train(dict(objective='binary',num_leaves=5,min_data_in_leaf=5,num_threads=1,seed=31,verbose=-1),lgb.Dataset(X[train],label=y[train]),num_boost_round=1)
        scores={1:model.predict(X,raw_score=True,num_threads=1)};E5.R._MODEL_ARRAYS[s.name,1]=model_arrays(model,1)
        c=E5.build(s,scores,1,4,.2);idx=np.concatenate([np.flatnonzero(y),np.flatnonzero(split['neg_test'])])
        space=SimpleNamespace(X=X[idx].copy(),h=h[idx].copy(),sorted_m=np.sort(h[y]),member=y[idx].copy())
        legacy=J.Exe(s,scores,c,space);f=Online(c,space,legacy);queries=np.arange(len(idx),dtype=np.int64)
        _,old=legacy.run(queries,0,len(queries),1,legacy.fresh_cache());new=f.all_probes(queries)
        np.testing.assert_array_equal(new==1,old.astype(bool));self.assertTrue(np.all(new[:150]==1));self.assertEqual(len(f.region_cuts),4)
        self.assertFalse(hasattr(f,'member'));self.assertFalse(hasattr(f,'space'));self.assertFalse(hasattr(f,'learned'))


if __name__=='__main__':unittest.main()
