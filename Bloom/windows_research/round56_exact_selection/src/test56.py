import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import common56 as S
import test55


class TimingTests(unittest.TestCase):
    def test_balanced_method_order(self):
        orders=[S.order(r) for r in range(3)]
        self.assertTrue(all(set(o)==set(S.METHODS) for o in orders))
        for pos in range(3):self.assertEqual({o[pos] for o in orders},set(S.METHODS))

    def test_complete_unique_matrix(self):
        keys={(ds,k,m,r) for ds,k in S.SETTINGS for r in range(3) for m in S.order(r)}
        self.assertEqual(len(keys),72)

    def test_trace_view_owns_full_parent(self):
        base=S.np.zeros(100,S.np.int64);view=base[10:35]
        ledger=S.owner_bytes(view)
        self.assertEqual(ledger['logical_owner_payload_bytes'],800)
        self.assertEqual(ledger['owner_physical_bytes'],sys.getsizeof(base))
        self.assertEqual(view.nbytes,200)
        self.assertTrue(ledger['owns_data'])

    def test_all_eight_references_are_fixed_workloads(self):
        for ds,k in S.SETTINGS:
            p,c=S.reference(ds,k)
            self.assertEqual(c['case']['seed'],0)
            self.assertEqual(c['case']['workload'],'真实轨迹' if ds.endswith('_flow') else 'zipf1.0-全部')
            self.assertEqual(c['status'],'complete')

    def test_regression_rejects_state_change(self):
        _,case=S.reference('url',128);old=next(r for r in case['rows'] if r['method']=='RA6');row=dict(old)
        S.check_regression(row,old)
        row['cache_sha']='x'*64
        with self.assertRaises(AssertionError):S.check_regression(row,old)

    def test_rates_are_not_omitted_from_state(self):
        lm=S.C.summarize19(S.np.array([0,0,1,2,2,2],S.np.int64))
        payload=lm.keys.nbytes+lm.counts.nbytes+lm.rate.nbytes
        self.assertEqual(payload,len(lm.keys)*24)
        self.assertGreater(sum(sys.getsizeof(x) for x in (lm.keys,lm.counts,lm.rate)),payload)


if __name__=='__main__':
    suite=unittest.TestSuite([unittest.defaultTestLoader.loadTestsFromModule(test55.test53),
                            unittest.defaultTestLoader.loadTestsFromTestCase(test55.Tests),
                            unittest.defaultTestLoader.loadTestsFromTestCase(TimingTests)])
    assert suite.countTestCases()==22
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    raise SystemExit(0 if result.wasSuccessful() else 1)
