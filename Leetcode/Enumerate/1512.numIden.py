from typing import List
from collections import defaultdict
class Solution:
    def numIdenticalPairs(self, nums: List[int]) -> int:
        res = 0
        d = defaultdict()
        for x in nums:
            res+=d[x]
            d[x]+=1

        return res