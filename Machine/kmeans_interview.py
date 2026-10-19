'''面试白板版：最基础的 K-Means 实现。'''
def distance_squared(a, b):
    '''返回两个点的欧氏距离平方；比较远近时不必开平方。'''
    return sum((x - y) ** 2 for x, y in zip(a, b))


def kmeans(points, k, max_iter=100):
    '''将二维或多维样本分成 k 个簇，返回聚类中心和每个点的标签。

    为了让核心逻辑清晰：直接用前 k 个样本作为初始中心。
    '''
    if not points or k <= 0 or k > len(points):
        raise ValueError("k 必须大于 0，且不能超过样本数量")

    centers = [point[:] for point in points[:k]]

    for _ in range(max_iter):
        # 1. 每个点分给最近的中心。
        labels = [
            min(range(k), key=lambda i: distance_squared(point, centers[i]))
            for point in points
        ]

        # 2. 每个中心更新为该簇所有点的平均值。
        new_centers = []
        for i in range(k):
            cluster = [point for point, label in zip(points, labels) if label == i]

            # 空簇时保持旧中心；面试中说明这一点即可。
            if not cluster:
                new_centers.append(centers[i])
            else:
                new_centers.append([
                    sum(point[d] for point in cluster) / len(cluster)
                    for d in range(len(points[0]))
                ])

        # 3. 中心没有变化，说明已收敛。
        if new_centers == centers:
            break
        centers = new_centers

    return centers, labels


if __name__ == "__main__":
    points = [[1, 1], [1, 2], [2, 1], [8, 8], [8, 9], [9, 8]]
    centers, labels = kmeans(points, k=2)

    print("聚类中心：", centers)
    print("样本标签：", labels)
