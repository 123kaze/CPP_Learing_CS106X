import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from cost34 import *
import unittest,sqlite3


class Clock:
    def __init__(self):self.value=-1000
    def __call__(self):self.value+=1000;return self.value


class Filter:
    def __init__(self):self.cached=set()
    def probe(self,x):return 0 if x==2 else 2 if x in self.cached else 1
    def absent(self,x):self.cached.add(x);return 1


class Tests(unittest.TestCase):
    def test_cost_only_on_actual_backend_responses(self):
        con=sqlite3.connect(':memory:');self.addCleanup(con.close)
        con.execute('create table kv(key integer primary key,value blob)');con.execute('insert into kv values(20,?)',(b'v',))
        flt=Filter();proxy=BackendCostCursor(con.cursor(),5,Clock());mask=np.zeros(5,np.uint8)
        r=online_run(proxy,'select value from kv where key=?',np.array([10,20,30],np.int64),np.array([0,0,1,1,2],np.int64),flt,mask)
        np.testing.assert_array_equal(mask,[1,0,1,1,0]);self.assertEqual((r['fp'],r['members_found'],r['backend_calls']),(1,2,3))
        self.assertEqual(proxy.calls,3);self.assertEqual(proxy.busy_wait_ns,15000);self.assertEqual(proxy.min_wait_ns,5000);self.assertEqual(flt.cached,{0});proxy.close()

    def test_zero_extra_cost_never_reads_wait_clock(self):
        con=sqlite3.connect(':memory:');self.addCleanup(con.close)
        def forbidden():raise AssertionError('delta0 must not enter timer loop')
        proxy=BackendCostCursor(con.cursor(),0,forbidden)
        self.assertEqual(proxy.execute('select 7',()).fetchone(),(7,));self.assertEqual(proxy.calls,1);self.assertEqual(proxy.busy_wait_ns,0);self.assertIsNone(proxy.min_wait_ns);proxy.close()

    def test_backend_failure_cannot_admit(self):
        con=sqlite3.connect(':memory:');self.addCleanup(con.close);flt=Filter();proxy=BackendCostCursor(con.cursor(),5,Clock())
        with self.assertRaises(sqlite3.OperationalError):online_run(proxy,'select value from nonexistent where key=?',np.array([10],np.int64),np.array([0],np.int64),flt,np.zeros(1,np.uint8))
        self.assertEqual(flt.cached,set());self.assertEqual(proxy.calls,0);proxy.close()

    def test_positive_and_absent_SQL_results_both_wait(self):
        con=sqlite3.connect(':memory:');self.addCleanup(con.close);p=BackendCostCursor(con.cursor(),10,Clock())
        self.assertEqual(p.execute('select 1',()).fetchone(),(1,));self.assertIsNone(p.execute('select 1 where 0',()).fetchone())
        self.assertEqual(p.calls,2);self.assertEqual(p.busy_wait_ns,20000);p.close()
        with self.assertRaises(ValueError):BackendCostCursor(None,-1)


if __name__=='__main__':unittest.main()
