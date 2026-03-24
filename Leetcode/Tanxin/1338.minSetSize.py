from typing import List
from collections import Counter
class Solution:
    def minSetSize(self, arr: List[int]) -> int:
        if not arr:
            return 0
        count = Counter(arr)
        n = len(arr)
        time = 0
        tar = n/2
        val = list(count.values())
        val.sort()
        while n>tar:
            n -= val[-1]
            val.pop()
            time+=1

        return time
