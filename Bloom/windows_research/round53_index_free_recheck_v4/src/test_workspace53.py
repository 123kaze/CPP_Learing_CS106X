import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from common53 import E5,np
from workspace53 import release_query_regions
from types import SimpleNamespace
from unittest.mock import patch
import unittest


class WorkspaceTests(unittest.TestCase):
    def test_only_unused_region_array_removed(self):
        flags=np.array([True,False,True]);bits=np.array([5],np.uint8)
        st=SimpleNamespace(q_region=np.array([0,1,2],np.int32),fp_static=flags,bits=bits,used_bytes=111,est_fpr=.25)
        c=dict(structure=st,trees=1,frac=.1,cache_bytes=32)
        original=E5.build
        with patch.object(E5,'build',return_value=c) as mock:
            with release_query_regions() as stats:
                actual=E5.build('unchanged argument')
                mock.assert_called_once_with('unchanged argument')
                self.assertIs(actual,c);self.assertIs(st.fp_static,flags);self.assertIs(st.bits,bits)
                self.assertEqual(st.used_bytes,111);self.assertEqual(st.est_fpr,.25)
                self.assertFalse(hasattr(st,'q_region'))
                self.assertEqual(stats['arrays_released'],1);self.assertEqual(stats['cumulative_array_bytes'],12)
            self.assertIs(E5.build,mock)
        self.assertIs(E5.build,original)
    def test_none_and_exception_restore(self):
        original=E5.build
        with patch.object(E5,'build',return_value=None) as mock:
            with self.assertRaisesRegex(ValueError,'fixture'):
                with release_query_regions() as stats:
                    self.assertIsNone(E5.build());self.assertEqual(stats['arrays_released'],0)
                    raise ValueError('fixture')
            self.assertIs(E5.build,mock)
        self.assertIs(E5.build,original)


if __name__=='__main__':unittest.main(verbosity=2)
