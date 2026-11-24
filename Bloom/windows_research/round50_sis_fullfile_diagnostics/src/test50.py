import sys,unittest,tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import prepare50 as P
np=P.np

class Tests(unittest.TestCase):
    def test_negative_only_stream_keeps_original_boundary(self):
        previous=P.ROOT
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'cache').mkdir();ids=np.arange(1000,dtype=np.uint64);y=np.arange(1000)<500;first=np.arange(1000,dtype=np.int64)
            tr=np.tile(np.arange(500,1000,dtype=np.int64),2);order=np.arange(500,1500,dtype=np.int64)
            np.savez(root/'cache/sis_fullfile.npz',ids=ids,y=y,X=np.zeros((1000,20),np.float32),first=first,negative_trace=tr,negative_order=order,boundary=np.int64(750),prefix1_reject=np.zeros(1000,np.bool_),prefix2_reject=np.zeros(1000,np.bool_))
            try:
                P.ROOT=root;_,yy,X,sp,learn,tail,_=P.load(5001)
                self.assertFalse(np.any(sp['member_train']&(sp['neg_train']|sp['neg_val'])))
                self.assertTrue((first[sp['neg_train']|sp['neg_val']]<750).all())
                self.assertTrue(sp['neg_test'][750:].all());self.assertGreater(len(learn),0);self.assertGreater(len(tail),len(learn))
                self.assertTrue(np.all(yy==y))
            finally:P.ROOT=previous
    def test_prefix_uses_query_path_only(self):
        self.assertEqual(P.path_prefix(b'/studium/a?token=one',2),P.path_prefix(b'/studium/a?token=two',2))
        self.assertNotEqual(P.path_prefix(b'/other/a',1),P.path_prefix(b'/studium/a',1))

if __name__=='__main__':unittest.main()
