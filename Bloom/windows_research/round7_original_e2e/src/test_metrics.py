"""Small checks for the benchmark's aggregation and cold-start contract."""
import unittest
import numpy as np
import shared as S


class MetricsTest(unittest.TestCase):
    def test_counts_and_partial_batch(self):
        stream = np.arange(7, dtype=np.int64)
        states = []
        def fresh():
            state = []
            states.append(state)
            return state
        def run(stream, lo, hi, state):
            state.extend(stream[lo:hi])
            cnt = np.zeros(6, np.int64)
            cnt[1] = int((stream[lo:hi] % 2 == 0).sum())
            cnt[4] = hi - lo
            return cnt
        for batch in (1, 3, 1000):
            result = S.measure(run, fresh, stream, batch, 7)
            self.assertEqual(result['fp'], 4)
            self.assertEqual(result['fpr'], 4 / 7)
            self.assertEqual(result['model_calls'], 7)
            self.assertEqual(states[-1], list(stream))
        self.assertEqual(len(states), 3)
        self.assertIsNot(states[0], states[1])

    def test_false_negatives_fail(self):
        def run(stream, lo, hi, state):
            return np.array([0, 0, 1, 0, 0, 0])
        with self.assertRaises(AssertionError):
            S.measure(run, lambda: None, np.array([0]), 1, 0)


if __name__ == '__main__':
    unittest.main()
