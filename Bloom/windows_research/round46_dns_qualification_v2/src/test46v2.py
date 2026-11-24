import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from adapter46v2 import fields,validate

class Tests(unittest.TestCase):
    def fixture(self,code=b'3',name=b'NXDOMAIN'):
        x=[b'-']*23;x[0]=b'1234.5';x[8]=b'example.test';x[11]=b'1';x[12]=b'A';x[13]=code;x[14]=name;return x
    def test_mapping(self):
        f=fields();self.assertEqual(len(f),23);self.assertEqual(f[8],b'query');self.assertEqual(f[20],b'answers');self.assertEqual(len(set(f)),23)
    def test_type_and_response_crosscheck(self):
        for code,name in ((b'0',b'NOERROR'),(b'3',b'NXDOMAIN')):self.assertEqual(len(validate(b'\t'.join(self.fixture(code,name))+b'\n')),23)
        with self.assertRaises(ValueError):validate(b'\t'.join(self.fixture(b'3',b'NOERROR')))
    def test_bad_type_or_field_count(self):
        x=self.fixture();x[12]=b'AAAA'
        with self.assertRaises(ValueError):validate(b'\t'.join(x))
        with self.assertRaises(ValueError):validate(b'\t'.join(x[:-1]))

if __name__=='__main__':unittest.main()
