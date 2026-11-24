import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from audit46 import normalize,response,features

class Tests(unittest.TestCase):
    def test_dns_case_and_final_dot(self):
        self.assertEqual(normalize(b'WWW.Example.COM.'),b'www.example.com')
        self.assertEqual(normalize(b'xn--example.com'),b'xn--example.com')
    def test_no_invented_escape_or_root(self):
        for q in (b'',b'.',b'-',b'a\\x20b.com',b'a\x00b.com',b'\xff.com'):
            self.assertIsNone(normalize(q))
    def test_response_codes_not_cache_misses(self):
        self.assertEqual(response(b'3',b'-'),2)
        self.assertEqual(response(b'0',b'192.0.2.1'),1)
        for r,a in ((b'0',b'-'),(b'0',b'(empty)'),(b'2',b'-'),(b'5',b'-'),(b'-',b'-')):self.assertEqual(response(r,a),0)
    def test_query_only_features(self):
        f=features(b'www.example.com');self.assertEqual(len(f),32);self.assertEqual(f[24],3);self.assertTrue(f[28]);self.assertFalse(f[29]);self.assertGreater(f[27],0.)

if __name__=='__main__':unittest.main()
