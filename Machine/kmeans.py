'''一个不依赖第三方库的 K-Means 聚类算法实现。'''

from __future__ import annotations

import math
import random
from typing import Iterable, List, Optional, Sequence


Point = Sequence[float]


class KMeans:
    '''反复执行“分配样本”和“更新中心”，将数值点分为若干簇。

    参数
    ----------
    n_clusters:
        聚类数量 K。
    max_iter:
        “分配—更新”循环的最大轮数。
    tol:
        当所有中心的移动距离都不超过此值时停止迭代。
    random_state:
        可选的随机种子，用于复现结果。
    '''

    def __init__(
        self,
        n_clusters: int,
        max_iter: int = 300,
        tol: float = 1e-4,
        random_state: Optional[int] = None,
    ) -> None:
        '''初始化 K-Means 的配置和训练结果属性。

        参数：
            n_clusters: 目标簇数量 K。
            max_iter: 最大迭代次数。
            tol: 聚类中心移动距离的收敛阈值。
            random_state: 可选随机种子。
        '''
        if n_clusters <= 0:
            raise ValueError("n_clusters must be positive")
        if max_iter <= 0:
            raise ValueError("max_iter must be positive")
        if tol < 0:
            raise ValueError("tol must be non-negative")

        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.random_state = random_state

        self.cluster_centers_: List[List[float]] = []
        self.labels_: List[int] = []
        self.inertia_: float = 0.0
        self.n_iter_: int = 0
        self._dimension: Optional[int] = None

    @staticmethod
    def _squared_distance(a: Point, b: Point) -> float:
        '''计算两个点的欧氏距离平方，比较远近时无需开平方。'''
        return sum((x - y) ** 2 for x, y in zip(a, b))

    @staticmethod
    def _as_points(points: Iterable[Point]) -> List[List[float]]:
        '''将输入转为二维列表，并校验样本非空、维度一致且坐标有限。'''
        result = [list(point) for point in points]
        if not result:
            raise ValueError("points must not be empty")

        dimension = len(result[0])
        if dimension == 0:
            raise ValueError("points must have at least one dimension")
        if any(len(point) != dimension for point in result):
            raise ValueError("all points must have the same dimension")
        if any(not all(math.isfinite(value) for value in point) for point in result):
            raise ValueError("point coordinates must be finite numbers")
        return result

    def _nearest_cluster(self, point: Point) -> int:
        '''返回与给定点欧氏距离平方最小的聚类中心编号。'''
        return min(
            range(self.n_clusters),
            key=lambda cluster: self._squared_distance(point, self.cluster_centers_[cluster]),
        )

    def fit(self, points: Iterable[Point]) -> "KMeans":
        '''用样本训练模型，更新聚类中心、标签、误差平方和与迭代次数。

        参数：
            points: 待聚类的样本；每个样本是相同维度的数值序列。

        返回：
            训练后的当前 KMeans 对象，方便链式调用。
        '''
        data = self._as_points(points)
        if self.n_clusters > len(data):
            raise ValueError("n_clusters cannot exceed the number of points")

        self._dimension = len(data[0])
        rng = random.Random(self.random_state)
        initial_indices = rng.sample(range(len(data)), self.n_clusters)
        self.cluster_centers_ = [data[index][:] for index in initial_indices]

        for iteration in range(1, self.max_iter + 1):
            labels = [self._nearest_cluster(point) for point in data]
            new_centers = [[0.0] * self._dimension for _ in range(self.n_clusters)]
            counts = [0] * self.n_clusters

            for point, label in zip(data, labels):
                counts[label] += 1
                for dimension, value in enumerate(point):
                    new_centers[label][dimension] += value

            # 空簇没有样本可供求平均值。将其中心重置为当前距所属中心
            # 最远的点，避免除以零，也有机会在下一轮重新获得样本。
            for cluster in range(self.n_clusters):
                if counts[cluster] == 0:
                    farthest_index = max(
                        range(len(data)),
                        key=lambda index: self._squared_distance(
                            data[index], self.cluster_centers_[labels[index]]
                        ),
                    )
                    new_centers[cluster] = data[farthest_index][:]
                else:
                    new_centers[cluster] = [
                        total / counts[cluster] for total in new_centers[cluster]
                    ]

            largest_shift = max(
                math.sqrt(self._squared_distance(old, new))
                for old, new in zip(self.cluster_centers_, new_centers)
            )
            self.cluster_centers_ = new_centers
            self.n_iter_ = iteration

            if largest_shift <= self.tol:
                break

        # 最后一轮更新可能移动了中心，因此重新分配一次标签。
        self.labels_ = [self._nearest_cluster(point) for point in data]
        self.inertia_ = sum(
            self._squared_distance(point, self.cluster_centers_[label])
            for point, label in zip(data, self.labels_)
        )
        return self

    def predict(self, points: Iterable[Point]) -> List[int]:
        '''根据已训练的聚类中心，返回每个输入点所属的最近簇编号。'''
        if not self.cluster_centers_:
            raise RuntimeError("call fit() before predict()")

        data = self._as_points(points)
        if len(data[0]) != self._dimension:
            raise ValueError("point dimension does not match the fitted model")
        return [self._nearest_cluster(point) for point in data]

    def fit_predict(self, points: Iterable[Point]) -> List[int]:
        '''训练模型后，直接返回每个训练样本对应的簇标签。'''
        return self.fit(points).labels_


if __name__ == "__main__":
    samples = [
        [1.0, 1.0], [1.5, 2.0], [2.0, 1.0],
        [7.0, 7.0], [8.0, 8.0], [8.0, 7.0],
    ]

    model = KMeans(n_clusters=2, random_state=42).fit(samples)
    print("centers:", model.cluster_centers_)
    print("labels: ", model.labels_)
    print("inertia:", model.inertia_)
