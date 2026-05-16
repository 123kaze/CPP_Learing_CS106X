import hashlib
import math
import random
from bisect import bisect_left
from dataclasses import dataclass
from typing import Dict, List, Sequence, Tuple

import numpy as np
from sklearn.linear_model import LogisticRegression

try:
    from pybloom_live import BloomFilter as PyBloomFilter
except ImportError:
    PyBloomFilter = None


class Bloom:
    def __init__(self, hashNum, maxSize):
        self.hashNum = hashNum
        self.maxSize = maxSize
        self.Bitset = [0] * maxSize

    def _hash(self, num, i):
        data = f"{num}:{i}".encode()
        digest = hashlib.sha256(data).hexdigest()
        return int(digest, 16) % self.maxSize

    def add(self, num):
        for i in range(self.hashNum):
            self.Bitset[self._hash(num, i)] = 1

    def contains(self, num):
        return all(self.Bitset[self._hash(num, i)] == 1 for i in range(self.hashNum))


class PyBloom:
    def __init__(self, bit_count: int, item_count: int):
        self.bit_count = max(1, int(bit_count))
        self.item_count = max(1, int(item_count))
        self._empty = item_count <= 0

        if PyBloomFilter is None:
            self._fallback = Bloom(1, self.bit_count)
            self._filter = None
            return

        self._fallback = None
        self._filter = PyBloomFilter(
            capacity=self.item_count,
            error_rate=self._error_rate(self.bit_count, self.item_count),
        )

    def add(self, key):
        self._empty = False
        key = str(key)
        if self._filter is not None:
            self._filter.add(key)
        else:
            self._fallback.add(key)

    def contains(self, key):
        if self._empty:
            return False
        key = str(key)
        if self._filter is not None:
            return key in self._filter
        return self._fallback.contains(key)

    def _error_rate(self, bit_count: int, item_count: int) -> float:
        return max(1e-8, min(0.999999, 0.5 ** (bit_count * math.log(2) / item_count)))


@dataclass
class LinearSegment:
    left: float
    right: float
    slope: float
    intercept: float

    def predict(self, x: float) -> float:
        return self.slope * x + self.intercept


class PiecewiseLinearLBF:
    """
    Learned Bloom Filter using a piecewise linear regression model.

    Query rule:
    - If model score >= threshold, return True directly.
    - Otherwise query the backup Bloom filter.

    During training, every positive key rejected by the model is inserted into
    the backup Bloom filter, so trained positive keys have no false negatives.
    """

    def __init__(
        self,
        hashNum: int,
        maxSize: int,
        segmentNum: int = 8,
        threshold: float = 0.5,
    ):
        if hashNum <= 0:
            raise ValueError("hashNum must be positive")
        if maxSize <= 0:
            raise ValueError("maxSize must be positive")
        if segmentNum <= 0:
            raise ValueError("segmentNum must be positive")

        self.hashNum = hashNum
        self.maxSize = maxSize
        self.segmentNum = segmentNum
        self.threshold = threshold
        self.backup = PyBloom(maxSize, 0)
        self.segments: List[LinearSegment] = []
        self._trained = False
        self.tuning_report: Dict[str, float] = {}

    def train(self, positives: Sequence, negatives: Sequence = None):
        positives = list(positives)
        if not positives:
            raise ValueError("positives cannot be empty")

        if negatives is None:
            negatives = self._make_negative_samples(positives, len(positives))
        else:
            negatives = list(negatives)

        samples = self._make_training_samples(positives, negatives)
        self.segments = self._fit_segments(samples)
        self._rebuild_backup(positives)
        self._trained = True

    def train_auto(
        self,
        positives: Sequence,
        train_negatives: Sequence,
        validation_negatives: Sequence,
        total_bits: int,
        projected_items: int = None,
        segment_bits: int = 256,
        max_thresholds: int = 256,
    ) -> Dict[str, float]:
        positives = list(positives)
        train_negatives = list(train_negatives)
        validation_negatives = list(validation_negatives)
        if not positives:
            raise ValueError("positives cannot be empty")
        if not validation_negatives:
            raise ValueError("validation_negatives cannot be empty")

        if projected_items is None:
            projected_items = len(positives)

        samples = self._make_training_samples(positives, train_negatives)
        self.segments = self._fit_segments(samples)
        positive_scores = sorted(self._score(key) for key in positives)
        negative_scores = sorted(self._score(key) for key in validation_negatives)

        thresholds = self._candidate_thresholds(
            positive_scores,
            negative_scores,
            max_thresholds,
        )
        best_report = None
        best_threshold = self.threshold

        for threshold in thresholds:
            report = self._estimate_projected_fpr_from_scores(
                positive_scores,
                negative_scores,
                total_bits,
                projected_items,
                threshold,
                segment_bits,
            )
            if best_report is None or report["lbf_fpr"] < best_report["lbf_fpr"]:
                best_report = report
                best_threshold = threshold

        self.threshold = best_threshold
        self._rebuild_backup(positives)
        self._trained = True
        self.tuning_report = best_report
        return best_report

    def estimate_projected_fpr(
        self,
        positives: Sequence,
        validation_negatives: Sequence,
        total_bits: int,
        projected_items: int,
        threshold: float = None,
        segment_bits: int = 256,
    ) -> Dict[str, float]:
        if threshold is None:
            threshold = self.threshold

        model_bits = len(self.segments) * segment_bits
        backup_bits = max(1, total_bits - model_bits)
        backup_items = sum(1 for key in positives if self._score(key) < threshold)
        model_false_accepts = sum(
            1 for key in validation_negatives if self._score(key) >= threshold
        )

        alpha = model_false_accepts / len(validation_negatives)
        backup_ratio = backup_items / len(positives)
        projected_backup_items = round(projected_items * backup_ratio)
        backup_fpr = self._bloom_fpr(backup_bits, projected_backup_items)
        lbf_fpr = alpha + (1.0 - alpha) * backup_fpr
        baseline_fpr = self._bloom_fpr(total_bits, projected_items)

        return {
            "threshold": threshold,
            "model_bits": model_bits,
            "backup_bits": backup_bits,
            "alpha": alpha,
            "backup_positive_ratio": backup_ratio,
            "backup_fpr": backup_fpr,
            "lbf_fpr": lbf_fpr,
            "baseline_fpr": baseline_fpr,
            "improvement": baseline_fpr / lbf_fpr if lbf_fpr > 0 else math.inf,
        }

    def _estimate_projected_fpr_from_scores(
        self,
        positive_scores: Sequence[float],
        negative_scores: Sequence[float],
        total_bits: int,
        projected_items: int,
        threshold: float,
        segment_bits: int,
    ) -> Dict[str, float]:
        model_bits = len(self.segments) * segment_bits
        backup_bits = max(1, total_bits - model_bits)
        backup_items = bisect_left(positive_scores, threshold)
        false_accepts = len(negative_scores) - bisect_left(negative_scores, threshold)

        alpha = false_accepts / len(negative_scores)
        backup_ratio = backup_items / len(positive_scores)
        projected_backup_items = round(projected_items * backup_ratio)
        backup_fpr = self._bloom_fpr(backup_bits, projected_backup_items)
        lbf_fpr = alpha + (1.0 - alpha) * backup_fpr
        baseline_fpr = self._bloom_fpr(total_bits, projected_items)

        return {
            "threshold": threshold,
            "model_bits": model_bits,
            "backup_bits": backup_bits,
            "alpha": alpha,
            "backup_positive_ratio": backup_ratio,
            "backup_fpr": backup_fpr,
            "lbf_fpr": lbf_fpr,
            "baseline_fpr": baseline_fpr,
            "improvement": baseline_fpr / lbf_fpr if lbf_fpr > 0 else math.inf,
        }

    def add(self, key):
        if not self._trained:
            raise RuntimeError("train() must be called before add()")

        if self._score(key) < self.threshold:
            self.backup.add(key)

    def contains(self, key) -> bool:
        if not self._trained:
            raise RuntimeError("train() must be called before contains()")

        if self._score(key) >= self.threshold:
            return True
        return self.backup.contains(key)

    def predict_score(self, key) -> float:
        if not self._trained:
            raise RuntimeError("train() must be called before predict_score()")
        return self._score(key)

    def _score(self, key) -> float:
        x = self._feature(key)
        segment = self._find_segment(x)
        score = segment.predict(x)
        return max(0.0, min(1.0, score))

    def _make_training_samples(
        self,
        positives: Sequence,
        negatives: Sequence,
    ) -> List[Tuple[float, float]]:
        samples = [(self._feature(key), 1.0) for key in positives]
        samples.extend((self._feature(key), 0.0) for key in negatives)
        samples.sort(key=lambda item: item[0])
        return samples

    def _rebuild_backup(self, positives: Sequence):
        backup_items = [key for key in positives if self._score(key) < self.threshold]
        self.backup = PyBloom(self.maxSize, len(backup_items))
        for key in backup_items:
            self.backup.add(key)

    def _candidate_thresholds(
        self,
        positive_scores: Sequence[float],
        negative_scores: Sequence[float],
        max_thresholds: int,
    ) -> List[float]:
        scores = list(positive_scores)
        scores.extend(negative_scores)
        scores = sorted(set(scores))
        if not scores:
            return [self.threshold]

        candidates = [0.0, 1.0, scores[-1] + 1e-12]
        if len(scores) <= max_thresholds:
            candidates.extend(scores)
        else:
            for i in range(max_thresholds):
                index = round(i * (len(scores) - 1) / (max_thresholds - 1))
                candidates.append(scores[index])
        return sorted(set(candidates))

    def _find_segment(self, x: float) -> LinearSegment:
        for segment in self.segments:
            if segment.left <= x <= segment.right:
                return segment

        if x < self.segments[0].left:
            return self.segments[0]
        return self.segments[-1]

    def _fit_segments(self, samples: List[Tuple[float, float]]) -> List[LinearSegment]:
        segment_count = min(self.segmentNum, len(samples))
        chunk_size = (len(samples) + segment_count - 1) // segment_count
        segments = []

        for start in range(0, len(samples), chunk_size):
            chunk = samples[start:start + chunk_size]
            left = chunk[0][0]
            right = chunk[-1][0]
            slope, intercept = self._linear_regression(chunk)
            segments.append(LinearSegment(left, right, slope, intercept))

        return segments

    def _linear_regression(self, samples: List[Tuple[float, float]]) -> Tuple[float, float]:
        n = len(samples)
        if n == 1:
            return 0.0, samples[0][1]

        sum_x = sum(x for x, _ in samples)
        sum_y = sum(y for _, y in samples)
        sum_xx = sum(x * x for x, _ in samples)
        sum_xy = sum(x * y for x, y in samples)

        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 0.0, sum_y / n

        slope = (n * sum_xy - sum_x * sum_y) / denominator
        intercept = (sum_y - slope * sum_x) / n
        return slope, intercept

    def _feature(self, key) -> float:
        if isinstance(key, (int, float)):
            return float(key)

        data = repr(key).encode()
        digest = hashlib.sha256(data).hexdigest()
        return float(int(digest[:16], 16))

    def _make_negative_samples(self, positives: Sequence, count: int) -> List[int]:
        numeric_positives = [key for key in positives if isinstance(key, int)]
        if len(numeric_positives) != len(positives):
            raise ValueError("negatives are required when positives contain non-integer keys")

        positive_set = set(numeric_positives)
        low = min(numeric_positives)
        high = max(numeric_positives)
        span = max(1, high - low + 1)
        low -= span
        high += span

        negatives = []
        while len(negatives) < count:
            key = random.randint(low, high)
            if key not in positive_set:
                negatives.append(key)
        return negatives

    def _bloom_fpr(self, bit_count: int, item_count: int) -> float:
        if item_count <= 0:
            return 0.0

        hash_count = max(1, round((bit_count / item_count) * math.log(2)))
        return (1.0 - math.exp(-hash_count * item_count / bit_count)) ** hash_count


class FeaturePiecewiseLinearLBF:
    """
    Feature-aware learned Bloom filter.

    The backup Bloom filter stores original keys. The learned model uses a
    feature vector, so URL/COD structure is preserved instead of being erased
    by hashing the key before learning.
    """

    def __init__(
        self,
        maxSize: int,
        segmentNum: int = 128,
        threshold: float = 0.5,
        ridge: float = 1e-4,
    ):
        if maxSize <= 0:
            raise ValueError("maxSize must be positive")
        if segmentNum <= 0:
            raise ValueError("segmentNum must be positive")

        self.maxSize = maxSize
        self.segmentNum = segmentNum
        self.threshold = threshold
        self.ridge = ridge
        self.score_epsilon = 1e-9
        self.backup = PyBloom(maxSize, 0)
        self.mean = None
        self.std = None
        self.weights = None
        self.bias = 0.0
        self.segments: List[LinearSegment] = []
        self._trained = False
        self.tuning_report: Dict[str, float] = {}

    def train_auto(
        self,
        positive_keys: Sequence,
        X_positive,
        X_negative,
        X_validation_negative,
        total_bits: int,
        segment_bits: int = 256,
        max_thresholds: int = 256,
    ) -> Dict[str, float]:
        positive_keys = list(positive_keys)
        X_positive = self._as_matrix(X_positive)
        X_negative = self._as_matrix(X_negative)
        X_validation_negative = self._as_matrix(X_validation_negative)

        if not positive_keys:
            raise ValueError("positive_keys cannot be empty")
        if len(positive_keys) != len(X_positive):
            raise ValueError("positive_keys and X_positive must have the same length")
        if len(X_negative) == 0:
            raise ValueError("X_negative cannot be empty")
        if len(X_validation_negative) == 0:
            raise ValueError("X_validation_negative cannot be empty")

        X_train = np.vstack([X_positive, X_negative])
        y_train = np.concatenate([
            np.ones(len(X_positive), dtype=np.float64),
            np.zeros(len(X_negative), dtype=np.float64),
        ])

        raw_train = self._fit_projection(X_train, y_train)
        self.segments = self._fit_segments_from_arrays(raw_train, y_train)

        positive_scores = np.sort(self.score_many(X_positive))
        negative_scores = np.sort(self.score_many(X_validation_negative))
        thresholds = self._candidate_thresholds(positive_scores, negative_scores, max_thresholds)

        best_report = None
        best_threshold = self.threshold
        for threshold in thresholds:
            report = self._estimate_from_scores(
                positive_scores,
                negative_scores,
                total_bits,
                len(positive_keys),
                threshold,
                segment_bits,
            )
            if best_report is None or report["lbf_fpr"] < best_report["lbf_fpr"]:
                best_report = report
                best_threshold = threshold

        self.threshold = best_threshold
        backup_mask = self.score_many(X_positive) < self.threshold + self.score_epsilon
        backup_keys = [key for key, keep in zip(positive_keys, backup_mask) if keep]
        self.backup = PyBloom(self.maxSize, len(backup_keys))
        for key in backup_keys:
            self.backup.add(key)

        self._trained = True
        self.tuning_report = best_report
        return best_report

    def contains(self, key, features) -> bool:
        if not self._trained:
            raise RuntimeError("train_auto() must be called before contains()")
        if self.score_one(features) >= self.threshold - self.score_epsilon:
            return True
        return self.backup.contains(key)

    def score_one(self, features) -> float:
        return float(self.score_many(np.asarray(features, dtype=np.float64).reshape(1, -1))[0])

    def score_many(self, X):
        if self.weights is None or not self.segments:
            raise RuntimeError("model is not trained")

        X = self._as_matrix(X)
        raw = self._project(X)
        rights = np.asarray([segment.right for segment in self.segments], dtype=np.float64)
        indexes = np.searchsorted(rights, raw, side="right")
        indexes = np.clip(indexes, 0, len(self.segments) - 1)

        slopes = np.asarray([segment.slope for segment in self.segments], dtype=np.float64)
        intercepts = np.asarray([segment.intercept for segment in self.segments], dtype=np.float64)
        scores = slopes[indexes] * raw + intercepts[indexes]
        return np.clip(scores, 0.0, 1.0)

    def _fit_projection(self, X, y):
        X = self._as_matrix(X)
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std[self.std == 0] = 1.0

        X_norm = (X - self.mean) / self.std
        X_aug = np.column_stack([X_norm, np.ones(len(X_norm))])
        reg = self.ridge * np.eye(X_aug.shape[1])
        reg[-1, -1] = 0.0
        params = np.linalg.solve(X_aug.T @ X_aug + reg, X_aug.T @ y)
        self.weights = params[:-1]
        self.bias = float(params[-1])
        return X_aug @ params

    def _project(self, X):
        X = self._as_matrix(X)
        return ((X - self.mean) / self.std) @ self.weights + self.bias

    def _fit_segments_from_arrays(self, raw, labels) -> List[LinearSegment]:
        order = np.argsort(raw)
        raw = np.asarray(raw, dtype=np.float64)[order]
        labels = np.asarray(labels, dtype=np.float64)[order]
        segment_count = min(self.segmentNum, len(raw))
        chunks = np.array_split(np.arange(len(raw)), segment_count)

        segments = []
        for indexes in chunks:
            xs = raw[indexes]
            ys = labels[indexes]
            left = float(xs[0])
            right = float(xs[-1])
            if len(xs) == 1:
                slope = 0.0
                intercept = float(ys[0])
            else:
                x_mean = xs.mean()
                y_mean = ys.mean()
                denom = float(((xs - x_mean) ** 2).sum())
                if denom == 0.0:
                    slope = 0.0
                    intercept = float(y_mean)
                else:
                    slope = float(((xs - x_mean) * (ys - y_mean)).sum() / denom)
                    intercept = float(y_mean - slope * x_mean)
            segments.append(LinearSegment(left, right, slope, intercept))
        return segments

    def _candidate_thresholds(self, positive_scores, negative_scores, max_thresholds: int):
        scores = np.unique(np.concatenate([positive_scores, negative_scores]))
        if len(scores) == 0:
            return np.asarray([self.threshold], dtype=np.float64)
        if len(scores) <= max_thresholds:
            candidates = scores
        else:
            indexes = np.linspace(0, len(scores) - 1, max_thresholds).round().astype(int)
            candidates = scores[indexes]
        return np.unique(np.concatenate([[0.0, 1.0, scores[-1] + 1e-12], candidates]))

    def _estimate_from_scores(
        self,
        positive_scores,
        negative_scores,
        total_bits: int,
        projected_items: int,
        threshold: float,
        segment_bits: int,
    ) -> Dict[str, float]:
        model_bits = len(self.segments) * segment_bits
        backup_bits = max(1, total_bits - model_bits)
        backup_items = int(np.searchsorted(positive_scores, threshold, side="left"))
        false_accepts = len(negative_scores) - int(np.searchsorted(negative_scores, threshold, side="left"))

        alpha = false_accepts / len(negative_scores)
        backup_ratio = backup_items / len(positive_scores)
        projected_backup_items = round(projected_items * backup_ratio)
        backup_fpr = self._bloom_fpr(backup_bits, projected_backup_items)
        lbf_fpr = alpha + (1.0 - alpha) * backup_fpr
        baseline_fpr = self._bloom_fpr(total_bits, projected_items)

        return {
            "threshold": float(threshold),
            "model_bits": model_bits,
            "backup_bits": backup_bits,
            "alpha": alpha,
            "backup_positive_ratio": backup_ratio,
            "backup_fpr": backup_fpr,
            "lbf_fpr": lbf_fpr,
            "baseline_fpr": baseline_fpr,
            "improvement": baseline_fpr / lbf_fpr if lbf_fpr > 0 else math.inf,
        }

    def _bloom_fpr(self, bit_count: int, item_count: int) -> float:
        if item_count <= 0:
            return 0.0
        hash_count = max(1, round((bit_count / item_count) * math.log(2)))
        return (1.0 - math.exp(-hash_count * item_count / bit_count)) ** hash_count

    def _as_matrix(self, X):
        X = np.asarray(X, dtype=np.float64)
        if X.ndim == 1:
            X = X.reshape(-1, 1)
        return X


class LogisticFeaturePiecewiseLinearLBF(FeaturePiecewiseLinearLBF):
    """
    Feature-aware LBF that uses logistic regression as the projection model
    before piecewise calibration.
    """

    def __init__(
        self,
        maxSize: int,
        segmentNum: int = 128,
        threshold: float = 0.5,
        C: float = 1.0,
        max_iter: int = 300,
    ):
        super().__init__(maxSize=maxSize, segmentNum=segmentNum, threshold=threshold)
        self.C = C
        self.max_iter = max_iter
        self.classifier = None

    def _fit_projection(self, X, y):
        X = self._as_matrix(X)
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std[self.std == 0] = 1.0
        X_norm = (X - self.mean) / self.std

        self.classifier = LogisticRegression(
            C=self.C,
            max_iter=self.max_iter,
            solver="lbfgs",
            n_jobs=1,
        )
        self.classifier.fit(X_norm, y)
        self.weights = self.classifier.coef_[0].astype(np.float64)
        self.bias = float(self.classifier.intercept_[0])
        return self._project(X)


class MultiProjectionFeaturePiecewiseLinearLBF(FeaturePiecewiseLinearLBF):
    """
    Feature-aware LBF with multiple generic logistic projections.

    Feature subspaces are generated without dataset-specific rules:
    - one full-feature projection
    - several deterministic random feature subsets

    The combined projection is then calibrated by the same piecewise model.
    """

    def __init__(
        self,
        maxSize: int,
        segmentNum: int = 128,
        threshold: float = 0.5,
        projection_count: int = 4,
        feature_fraction: float = 0.7,
        aggregation: str = "max",
        C: float = 1.0,
        max_iter: int = 300,
        random_state: int = 7,
    ):
        super().__init__(maxSize=maxSize, segmentNum=segmentNum, threshold=threshold)
        if projection_count <= 0:
            raise ValueError("projection_count must be positive")
        if not 0 < feature_fraction <= 1:
            raise ValueError("feature_fraction must be in (0, 1]")
        if aggregation not in {"max", "mean"}:
            raise ValueError("aggregation must be 'max' or 'mean'")

        self.projection_count = projection_count
        self.feature_fraction = feature_fraction
        self.aggregation = aggregation
        self.C = C
        self.max_iter = max_iter
        self.random_state = random_state
        self.projections = []

    def _fit_projection(self, X, y):
        X = self._as_matrix(X)
        self.mean = X.mean(axis=0)
        self.std = X.std(axis=0)
        self.std[self.std == 0] = 1.0
        X_norm = (X - self.mean) / self.std

        groups = self._make_feature_groups(X_norm.shape[1])
        self.projections = []
        raw_scores = []

        for index, columns in enumerate(groups):
            classifier = LogisticRegression(
                C=self.C,
                max_iter=self.max_iter,
                solver="lbfgs",
                n_jobs=1,
                random_state=self.random_state + index,
            )
            classifier.fit(X_norm[:, columns], y)
            self.projections.append((columns, classifier))
            raw_scores.append(classifier.decision_function(X_norm[:, columns]))

        self.weights = np.ones(X_norm.shape[1], dtype=np.float64)
        self.bias = 0.0
        return self._aggregate_scores(np.column_stack(raw_scores))

    def _project(self, X):
        X = self._as_matrix(X)
        X_norm = (X - self.mean) / self.std
        raw_scores = []
        for columns, classifier in self.projections:
            raw_scores.append(classifier.decision_function(X_norm[:, columns]))
        return self._aggregate_scores(np.column_stack(raw_scores))

    def _make_feature_groups(self, feature_count: int):
        groups = [np.arange(feature_count)]
        if self.projection_count == 1:
            return groups

        rng = np.random.default_rng(self.random_state)
        subset_size = max(1, int(round(feature_count * self.feature_fraction)))
        for _ in range(self.projection_count - 1):
            columns = np.sort(rng.choice(feature_count, size=subset_size, replace=False))
            groups.append(columns)
        return groups

    def _aggregate_scores(self, scores):
        if self.aggregation == "mean":
            return scores.mean(axis=1)
        return scores.max(axis=1)
