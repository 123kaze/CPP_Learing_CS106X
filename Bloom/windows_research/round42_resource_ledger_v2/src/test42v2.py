import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit42v2 import storage,np

class Tests(unittest.TestCase):
    def test_owner(self):
        a=np.zeros(10,np.uint64);s=storage(a)
        self.assertEqual(s['logical_payload_bytes'],80);self.assertEqual(s['retained_chain_bytes'],sys.getsizeof(a))
    def test_reshape_view(self):
        a=np.zeros(100,np.float32);v=a.reshape(10,10);s=storage(v)
        self.assertEqual(s['retained_chain_bytes'],sys.getsizeof(a)+sys.getsizeof(v));self.assertEqual(s['logical_payload_bytes'],400)
    def test_nonowning_bytes(self):
        b=bytes(100);v=np.frombuffer(b,np.uint8);s=storage(v)
        self.assertEqual(s['retained_chain_bytes'],sys.getsizeof(b)+sys.getsizeof(v));self.assertEqual(s['logical_payload_bytes'],100)

if __name__=='__main__':unittest.main()
