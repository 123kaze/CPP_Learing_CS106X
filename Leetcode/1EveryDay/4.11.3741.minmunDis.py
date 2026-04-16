from typing import List
from collections import defaultdict

class Solution:
    def minimumDistance(self, nums: List[int]) -> int:
        pos = defaultdict(list)
        for idx, val in enumerate(nums):
            pos[val].append(idx)

        min_span = float('inf')
        for indices in pos.values():
            if len(indices) >= 3:
                for i in range(len(indices) - 2):
                    span = indices[i+2] - indices[i]
                    if span < min_span:
                        min_span = span

        return -1 if min_span == float('inf') else min_span * 2