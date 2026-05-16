import hashlib


class Bloom:
    def __init__(self, hash_num, size):
        self.hash_num = hash_num
        self.size = size
        self.bits = [0] * size

    def _hash(self, key, i):
        text = str(key) + ":" + str(i)
        value = hashlib.sha256(text.encode()).hexdigest()
        return int(value, 16) % self.size

    def add(self, key):
        for i in range(self.hash_num):
            index = self._hash(key, i)
            self.bits[index] = 1

    def contains(self, key):
        for i in range(self.hash_num):
            index = self._hash(key, i)
            if self.bits[index] == 0:
                return False
        return True


class EasyLearnedBloom:
    def __init__(self, segment_num=4, threshold=0.5, bloom_size=100, hash_num=3):
        self.segment_num = segment_num
        self.threshold = threshold
        self.backup = Bloom(hash_num, bloom_size)
        self.segments = []

    def train(self, positives, negatives):
        data = []

        for x in positives:
            data.append((x, 1))

        for x in negatives:
            data.append((x, 0))

        data.sort()
        self._fit_segments(data)

        for x in positives:
            score = self.predict_score(x)
            if score < self.threshold:
                self.backup.add(x)

    def contains(self, key):
        score = self.predict_score(key)

        if score >= self.threshold:
            return True

        return self.backup.contains(key)

    def predict_score(self, key):
        for left, right, a, b in self.segments:
            if left <= key <= right:
                score = a * key + b
                return self._limit(score)

        if key < self.segments[0][0]:
            left, right, a, b = self.segments[0]
        else:
            left, right, a, b = self.segments[-1]

        score = a * key + b
        return self._limit(score)

    def _fit_segments(self, data):
        n = len(data)
        part_size = max(1, n // self.segment_num)

        self.segments = []

        start = 0
        while start < n:
            part = data[start:start + part_size]
            left = part[0][0]
            right = part[-1][0]
            a, b = self._linear_fit(part)
            self.segments.append((left, right, a, b))
            start += part_size

    def _linear_fit(self, part):
        n = len(part)

        sum_x = 0
        sum_y = 0
        sum_xx = 0
        sum_xy = 0

        for x, y in part:
            sum_x += x
            sum_y += y
            sum_xx += x * x
            sum_xy += x * y

        bottom = n * sum_xx - sum_x * sum_x

        if bottom == 0:
            return 0, sum_y / n

        a = (n * sum_xy - sum_x * sum_y) / bottom
        b = (sum_y - a * sum_x) / n
        return a, b

    def _limit(self, score):
        if score < 0:
            return 0
        if score > 1:
            return 1
        return score


if __name__ == "__main__":
    positives = [10, 11, 12, 13, 50, 51, 52, 90, 91]
    negatives = [1, 2, 3, 30, 31, 70, 71, 100, 101]

    lbf = EasyLearnedBloom(
        segment_num=3,
        threshold=0.5,
        bloom_size=100,
        hash_num=3,
    )

    lbf.train(positives, negatives)

    tests = [10, 11, 30, 51, 70, 90, 200]

    for x in tests:
        print(x, lbf.contains(x), "score =", round(lbf.predict_score(x), 3))
