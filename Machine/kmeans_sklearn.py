"""K-Means using scikit-learn instead of a hand-written implementation.

Install the dependency first:
    python3 -m pip install scikit-learn
"""

from sklearn.cluster import KMeans


def main() -> None:
    samples = [
        [1.0, 1.0], [1.5, 2.0], [2.0, 1.0],
        [7.0, 7.0], [8.0, 8.0], [8.0, 7.0],
    ]

    model = KMeans(
        n_clusters=2,
        init="k-means++",  # sklearn's recommended centroid initialization
        n_init=10,          # use several initializations and retain the best one
        max_iter=300,
        random_state=42,
    )

    labels = model.fit_predict(samples)

    print("centers:", model.cluster_centers_.tolist())
    print("labels: ", labels.tolist())
    print("inertia:", model.inertia_)

    new_points = [[1.2, 1.1], [7.5, 7.5]]
    print("new point labels:", model.predict(new_points).tolist())


if __name__ == "__main__":
    main()
