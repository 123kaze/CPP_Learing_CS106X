from typing import List
from collections import defaultdict

class Solution:
    def splitPainting(self, segments: List[List[int]]) -> List[List[int]]:
        diff = defaultdict(int)

        for start, end, color in segments:
            diff[start] += color
            diff[end] -= color

        ans = []
        cur = 0
        prev = None

        for x in sorted(diff):
            if prev is not None and prev < x and cur != 0:
                ans.append([prev, x, cur])

            cur += diff[x]
            prev = x

        return ans


