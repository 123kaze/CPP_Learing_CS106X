import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import unittest
import numpy as np
from audit29 import clustered,collision_check,group


class Tests(unittest.TestCase):
    def test_paired_dataset_cluster_constant_effect(self):
        rows=[]
        counts=[4,4,4,4,2,1,1,1]
        names=['uniform-1万','zipf1.0-10万','zipf1.0-100万','uniform-全部']
        for ds,n in enumerate(counts):
            for w in names[:n]:rows.append(dict(dataset=str(ds),workload=w,replay_fp=99,repaired_ra_fp=79))
        r=clustered(rows,'repaired_ra_fp');self.assertEqual(r['original_cluster_count'],21)
        self.assertAlmostEqual(r['original_equal_cluster_ratio'],.8)
        np.testing.assert_allclose(r['dataset_cluster_percentile95'],[.8,.8],atol=1e-15)
        np.testing.assert_allclose(r['equal_dataset_percentile95'],[.8,.8],atol=1e-15)

    def test_collision_limits(self):
        r=collision_check();self.assertFalse(r['prefix_member_rejected']);self.assertTrue(r['fp64_member_rejected']);self.assertFalse(r['real_collision_discovered'])

    def test_original_workload_groups(self):
        self.assertEqual(group('zipf1.2-全部'),'全部 key 池');self.assertEqual(group('真实轨迹'),'真实轨迹');self.assertEqual(group('全新对抗'),'每key一次/全新对抗')


if __name__=='__main__':unittest.main()
