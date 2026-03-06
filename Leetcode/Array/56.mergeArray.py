from typing import List


class Solution:
    def merge(self, intervals: List[List[int]]) -> List[List[int]]:
        res = []
        intervals.sort(key=lambda x: (x[0], -x[1]))
        n = len(intervals)
        for data in intervals:
            if not res or res[-1][1] < data[0]:
                res.append(data)
            else:
                res[-1][1] = max(res[-1][1], data[1])
        return res
