import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from data48 import HTTP,stable_arrays,path_prefix,np

class Tests(unittest.TestCase):
    def test_combined_log_and_query_retained(self):
        line=b'192.0.2.1 - anon [01/May/2018:09:00:00 +0200] "GET /studium/a?x=1 HTTP/1.1" 404 12 "-" "fixture-agent"\n'
        item,why=HTTP.decode_line(line);self.assertIsNone(why);self.assertEqual(item[1],b'/studium/a?x=1');self.assertEqual(item[2],404);self.assertEqual(item[0].utcoffset().total_seconds(),7200)
    def test_non_get_and_bad_date(self):
        line=b'192.0.2.1 - anon [01/May/2018:09:00:00 +0200] "POST /x HTTP/1.1" 200 12 "-" "fixture"\n'
        item,why=HTTP.decode_line(line);self.assertIsNone(item);self.assertEqual(why,'non_GET')
        item,why=HTTP.decode_line(line.replace(b'POST',b'GET').replace(b'01/May',b'40/May'));self.assertIsNone(item)
    def test_conflicts_removed_not_relabelled(self):
        keys=[b'/a?x=1',b'/b',b'/c'];flags=[1,3,2];first=[0,1,4]
        a,stats,rules=stable_arrays(keys,flags,first,[0,1,1,0,2,2],[0,1,2,3,4,5],[1,1,2,1,2,2],8)
        np.testing.assert_array_equal(a['y'],[True,False]);np.testing.assert_array_equal(a['order'],[0,3,4,5]);self.assertEqual(int(a['boundary']),2)
        self.assertEqual(stats['conflicting_404_requests'],1);self.assertEqual(stats['retained_404_requests'],2)
    def test_query_params_are_distinct_keys_not_rule_input(self):
        keys=[b'/studium/a?x=1',b'/studium/a?x=2'];a,_,r=stable_arrays(keys,[1,2],[0,3],[0,1],[0,3],[1,2],4)
        self.assertNotEqual(int(a['ids'][0]),int(a['ids'][1]));self.assertEqual(path_prefix(keys[0],2),path_prefix(keys[1],2))
        self.assertFalse(a['prefix2_reject'].any())
    def test_cheap_rule_never_rejects_static_member(self):
        keys=[b'/studium/a',b'/studium/b',b'/other/missing'];a,_,r=stable_arrays(keys,[1,1,2],[0,1,3],[0,1,2],[0,1,3],[1,1,2],4)
        self.assertFalse(a['prefix1_reject'][a['y']].any());self.assertTrue(a['prefix1_reject'][~a['y']].all());self.assertGreater(r['1']['packed_support_array_bytes'],0)

if __name__=='__main__':unittest.main()
