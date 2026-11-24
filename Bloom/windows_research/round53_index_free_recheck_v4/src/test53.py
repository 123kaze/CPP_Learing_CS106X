"""Run all 12 frozen cache/address tests plus two new workspace-lifetime tests."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common53,cache53,prepare53,test_workspace53
import frozen53
import unittest
original=frozen53.load('test53')

if __name__=='__main__':
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(original),unittest.defaultTestLoader.loadTestsFromModule(test_workspace53)])
    assert suite.countTestCases()==14
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
