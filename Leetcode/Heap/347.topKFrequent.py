from typing import List
from collections import Counter
class Solution:
    def topKFrequent(self, nums: List[int], k: int) -> List[int]:
        count = Counter(nums)
        maxc = max(count.values())
        buckets = [[]for _ in range(maxc+1)]
        for x,c in count.items():
            buckets[c].append(x)
        ans = []
        for bucket in reversed(buckets):
            ans+=bucket
            if len(ans) == k:
                return ans