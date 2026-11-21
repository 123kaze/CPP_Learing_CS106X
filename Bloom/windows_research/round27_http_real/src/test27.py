import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest
import gzip
import tempfile
import numpy as np
from data27 import lexical,parse,FEATURES
from worker27 import prepare,E5,B,evaluate


class Tests(unittest.TestCase):
    def test_features_no_outcome(self):
        x=lexical(b'/a/B12.gif?x=4')
        self.assertEqual(len(x),len(FEATURES));self.assertEqual(x[3],3);self.assertEqual(x[15],True)
        self.assertEqual(lexical(b'/a/B12.gif?x=4'),x)

    def test_conflicts_and_status_filtering(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/'data.gz';out=Path(tmp)/'data.npz'
            records=[(b'/ok',200),(b'/bad',404),(b'/flip',200),(b'/flip',404),(b'/skip',500),(b'/ok',304)]
            with gzip.open(source,'wb') as f:
                for target,status in records:f.write(b'host - - [01/Jul/1995:00:00:00 -0400] "GET '+target+b' HTTP/1.0" '+str(status).encode()+b' 1\n')
            meta=parse(source,out)
            self.assertEqual(meta['conflicting_keys'],1);self.assertEqual(meta['retained_404_requests'],1);self.assertEqual(meta['members'],1)
            with np.load(out) as d:self.assertEqual(len(d['trace']),3);self.assertEqual(d['boundary'],1)
            with self.assertRaises(AssertionError):parse(source,out)

    def test_split_and_budget_cache(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'fixture.npz';N=1000
            ids=np.arange(N,dtype=np.uint64);y=ids<500;X=np.zeros((N,20),np.float32)
            first=np.zeros(N,np.int64);first[900:]=500
            trace=np.tile(np.arange(N),4);order=np.arange(len(trace))
            np.savez(p,ids=ids,y=y,X=X,first=first,trace=trace,order=order,boundary=1000)
            s,_,learn,tail=prepare(p,2701)
            self.assertFalse(np.any(s.split['neg_train']&s.split['neg_test']))
            safe=E5.E.CC.safe_prefix_lengths(np.sort(s.h1m),s.h1q)
            for frac in (0.,.1,.6):
                c=B.build(s,4,frac,E5.K)
                self.assertLessEqual(c['structure'].used_bytes,4096)
                result,fn=evaluate(c,tail,s,safe);self.assertEqual(fn,0);self.assertEqual(result['processed'],len(tail))
                self.assertLessEqual(result['fp'],int(c['structure'].fp_static[tail].sum()))


if __name__=='__main__':unittest.main()
