import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from fetch47 import ranges,verified_range,TOTAL

class Tests(unittest.TestCase):
    def test_ranges_cover_exactly(self):
        for size in (17,TOTAL):
            rr=ranges(size);self.assertEqual(rr[0][0],0);self.assertEqual(rr[-1][1],size-1)
            self.assertEqual(sum(hi-lo+1 for lo,hi in rr),size)
            for a,b in zip(rr,rr[1:]):self.assertEqual(a[1]+1,b[0])
    def test_final_redirect_response(self):
        h='HTTP/1.1 302 Found\r\nLocation: https://example.org\r\n\r\nHTTP/2 206\r\nContent-Range: bytes 0-9/100\r\n\r\n'
        self.assertTrue(verified_range(h,0,9,100))
    def test_wrong_or_ignored_range(self):
        self.assertFalse(verified_range('HTTP/2 200\nContent-Range: bytes 0-9/100\n',0,9,100))
        self.assertFalse(verified_range('HTTP/2 206\nContent-Range: bytes 1-10/100\n',0,9,100))
        self.assertFalse(verified_range('HTTP/2 206\nContent-Range: bytes 0-9/101\n',0,9,100))

if __name__=='__main__':unittest.main()
