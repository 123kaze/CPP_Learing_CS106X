import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from inventory49 import database,add,flush,aggregate

class Tests(unittest.TestCase):
    def test_cross_batch_conflict_and_counts(self):
        with tempfile.TemporaryDirectory() as d:
            con=database(Path(d)/'test.sqlite');batch={}
            try:
                add(batch,b'/ok',1,0);add(batch,b'/conflict',1,1);add(batch,b'/absent',2,2);flush(con,batch)
                add(batch,b'/absent',2,4);add(batch,b'/conflict',2,5);add(batch,b'/ok',1,6);flush(con,batch)
                self.assertEqual(aggregate(con),dict(members=1,negative_keys=1,conflicting_keys=1,retained_404_requests=2,conflicting_404_requests=1,retained_success_requests=2,distinct_keys=3))
                self.assertEqual(con.execute('SELECT first_seen,last_seen FROM keys WHERE k=?',(b'/conflict',)).fetchone(),(1,5))
                self.assertEqual(batch,{})
            finally:con.close()
    def test_full_target_parameter_identity(self):
        with tempfile.TemporaryDirectory() as d:
            con=database(Path(d)/'test.sqlite');batch={}
            try:
                add(batch,b'/a?x=1',1,0);add(batch,b'/a?x=2',2,1);flush(con,batch);self.assertEqual(aggregate(con)['distinct_keys'],2)
            finally:con.close()
    def test_empty_catalogue(self):
        with tempfile.TemporaryDirectory() as d:
            con=database(Path(d)/'test.sqlite')
            try:self.assertTrue(all(x==0 for x in aggregate(con).values()))
            finally:con.close()

if __name__=='__main__':unittest.main()
