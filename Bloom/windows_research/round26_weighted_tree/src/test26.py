import unittest
import numpy as np
from weights26 import transfer_weights,FLOOR


class WeightTests(unittest.TestCase):
    def test_uniform_target_matches_training_density(self):
        bins=np.array([0,0,0,1]);w,meta=transfer_weights([3,1],bins)
        self.assertTrue(np.allclose(w,1))
    def test_class_total_preserved_and_shape_changes(self):
        bins=np.array([0,0,0,1]);w,meta=transfer_weights([1,3],bins)
        self.assertAlmostEqual(w.sum(),4);self.assertGreater(w[-1],w[0])
    def test_empty_target_bins_not_zero_training_weights(self):
        w,meta=transfer_weights([0,1,5],np.array([0,1,1]))
        self.assertTrue((w>0).all());self.assertLess(meta['supported_target_mass'],1)
    def test_invalid_mass_rejected(self):
        with self.assertRaises(ValueError):transfer_weights([0,0],np.array([0,1]))


if __name__=='__main__':unittest.main(verbosity=2)
