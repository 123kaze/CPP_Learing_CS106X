"""Check data partitioning and the source-tail-only Gama instrumentation."""
import ast
import unittest
from pathlib import Path
import numpy as np
import prepare_data as D


class ProtocolTest(unittest.TestCase):
    def test_partition_disjoint(self):
        ids = np.arange(10000, dtype=np.uint64)
        y = ids % 3 == 0
        u = (D.splitmix(ids ^ np.uint64(0x5EED)) >> np.uint64(11)).astype(np.float64) / 2 ** 53
        masks = [y & (u < .5), y & (u >= .5), ~y & (u < .1),
                 ~y & (u >= .1) & (u < .2), ~y & (u >= .2)]
        self.assertTrue((sum(x.astype(np.int64) for x in masks) == 1).all())

    def test_original_markers_unique(self):
        for variant in ('LBF', 'PLBF'):
            file = D.REPO / f'lgb_url_Gama{variant}_ada.py'
            source = file.read_text()
            loop = 'for size in range(64 * 1024, 320 * 1024 + 1, 64 * 1024):'
            marker = '    pos_scores = best_bst.predict(positive_items).tolist()' if variant == 'PLBF' else '    end_time = time.perf_counter_ns()'
            self.assertEqual(source.count(loop), 1)
            self.assertEqual(source.count(marker), 1)
            tree = ast.parse(source[:source.index(marker)] + '    finish(globals())\n')
            self.assertIsInstance(tree, ast.Module)
            self.assertIn('    optimize_epochs()\n', source[:source.index(marker)])


if __name__ == '__main__':
    unittest.main()
