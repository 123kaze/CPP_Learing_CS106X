import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from guard32 import *
from types import SimpleNamespace
from unittest.mock import patch
import unittest


def lm(counts):return SimpleNamespace(counts=np.array(counts,np.int64),L=sum(counts))
def candidate(t,e):return dict(trees=t,frac=0.,structure=SimpleNamespace(est_fpr=e))


class Tests(unittest.TestCase):
    def test_raw_count_boundary(self):
        self.assertTrue(no_repeat(lm([1,1,1])));self.assertFalse(no_repeat(lm([1,2])))
        with self.assertRaises(ValueError):no_repeat(lm([]))

    def test_same_Gama_tie_breaking_and_no_RA_path(self):
        candidates=[candidate(4,.2),candidate(2,.1),candidate(1,.1)]
        with patch.object(E5,'candidates',return_value=candidates) as build,patch.object(ra6,'select6',side_effect=AssertionError('Predictor entered')):
            c,info=select('setup','scores',lm([1,1]),8,100)
            self.assertIs(c,E5.gama(candidates));self.assertEqual(c['trees'],1);self.assertEqual(info['path'],'exact_Gama')
            build.assert_called_once_with('setup','scores',8,fracs=(0.,))

    def test_repeated_input_delegated_unchanged(self):
        counts=lm([1,2]);chosen=object();old=dict(trees=8,frac=.1)
        with patch.object(ra6,'select6',return_value=(chosen,old)) as call,patch.object(E5,'candidates',side_effect=AssertionError('Gama branch entered')):
            c,info=select('setup','scores',counts,128,300,topk=3)
            self.assertIs(c,chosen);call.assert_called_once_with('setup','scores',counts,128,300,topk=3)
            self.assertEqual(info['path'],'unchanged_RA6');self.assertEqual(info['trees'],8)


if __name__=='__main__':unittest.main()
