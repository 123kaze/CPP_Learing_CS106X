import sys
import unittest
import numpy as np
import baseline as B


class BaselineTests(unittest.TestCase):
    def test_frozen_bit_positions_and_accounting(self):
        rng = np.random.default_rng(77)
        members = rng.integers(0, 2**64 - 1, 5000, dtype=np.uint64)
        negatives = rng.integers(0, 2**64 - 1, 20000, dtype=np.uint64)
        for budget in (1024, 4096, 16384):
            with self.subTest(budget=budget):
                a = B.allocate(len(members), budget, 0)
                B.insert_all(a, members)
                m, k = int(a[1]), int(a[2])
                bits = np.zeros(m // 8, np.uint8)
                off, sizes, ks = np.array([0, m]), np.array([m]), np.array([k])
                B.R.packed_build(members, np.zeros(len(members), np.int32), off, sizes, ks, bits)
                self.assertTrue(np.array_equal(a[B.HEAD_WORDS:].view(np.uint8), bits))
                flags = B.R.packed_query(negatives, np.zeros(len(negatives), np.int32),
                                        np.array([B.C.BF], np.uint8), off, sizes, ks, bits)
                self.assertTrue(np.array_equal(B.query_all(a, negatives), flags))
                self.assertTrue(B.query_all(a, members).all())
                self.assertEqual(sys.getsizeof(a), B.ARRAY_HEADER + 32 + m // 8)
                self.assertLessEqual(sys.getsizeof(a), budget)

    def test_cache_bytes_and_query_reload(self):
        rng = np.random.default_rng(8)
        setup = B.SimpleNamespace(h1m=rng.integers(0, 2**63, 2000, dtype=np.uint64),
                                  h1q=rng.integers(0, 2**63, 10000, dtype=np.uint64))
        for cache in B.CACHES.values():
            c = B.build(setup, 4, .2, cache)
            st = c['structure']
            self.assertLessEqual(st.used_bytes, 4096)
            self.assertEqual(st.used_bytes, sys.getsizeof(st.data) + c['cache_bytes'])
            # Reconstruct from only the owning BF buffer, not the setup or a model.
            restored = np.frombuffer(st.data.tobytes(), np.uint64).copy()
            self.assertTrue(np.array_equal(B.query_all(restored, setup.h1q), st.fp_static))
            self.assertEqual(st.model_bytes, 0)

    def test_integer_k(self):
        self.assertEqual(B.optimal_k(1000, 1000), 1)
        for m in (1000, 2000, 8000, 16000):
            k = B.optimal_k(1000, m)
            scores = [(-np.expm1(-j * 1000 / m)) ** j for j in range(1, 20)]
            self.assertEqual(k, int(np.argmin(scores)) + 1)

    def test_loader_matches_frozen_prepared_url(self):
        # Existing prepared data only; no training/network. Skip on a fresh data-free clone.
        if not (B.C.CACHE / 'url/data.npz').exists():
            self.skipTest('prepared URL data not available')
        s, safe, _ = B.load_setup('url', 'fp64')
        self.assertIsNone(safe)
        self.assertFalse(hasattr(s, 'member_hashes'))
        old, _, _ = B.E5.load('url')
        for field in ('h1m', 'h1q', 'q_score'):
            self.assertTrue(np.array_equal(getattr(s, field), getattr(old, field)), field)
        for spec in (('uniform', 10000), ('fresh',)):
            self.assertTrue(np.array_equal(B.E5.base_stream(s, 'test', spec, 0, 10000),
                                           B.E5.base_stream(old, 'test', spec, 0, 10000)))


if __name__ == '__main__':
    unittest.main()
