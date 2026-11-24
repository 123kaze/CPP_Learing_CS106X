import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from namespace45 import vocabulary,encode,np,PAYLOAD

class Tests(unittest.TestCase):
    def test_vocabulary_full_physical_bytes(self):
        data=vocabulary([b'ns:one',b'ns:two',b'x:three'])
        self.assertEqual(PAYLOAD,336);self.assertEqual(data.nbytes,336);self.assertTrue(data.flags.owndata)
        self.assertEqual(sys.getsizeof(data),336+sys.getsizeof(np.empty(0,np.uint8)))
    def test_order_invariant_ties(self):
        keys=[b'a:1',b'b:2',b'a:3',b'b:4'];np.testing.assert_array_equal(vocabulary(keys),vocabulary(keys[::-1]))
    def test_unseen_validation_prefix_not_in_vocab(self):
        d=vocabulary([b'aa1',b'aa2']);x=encode([b'aa3',b'zz9'],d)
        self.assertEqual(x.shape,(2,64));self.assertGreater(x[0].sum(),0);self.assertEqual(x[1].sum(),0)
    def test_distinct_keys_and_short_keys(self):
        with self.assertRaises(ValueError):vocabulary([b'a',b'a'])
        d=vocabulary([b'a',b'ab']);x=encode([b'a',b'ab'],d)
        self.assertEqual(x[0].sum(),1);self.assertEqual(x[1].sum(),2)

if __name__=='__main__':unittest.main()
