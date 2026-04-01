from typing import List
from collections import Counter
from functools import reduce
from operator import xor
class Solution:
    def singleNumber(self, nums: List[int]) -> int:
        cnt = Counter(nums)
        for k, v in cnt.items():
            if v == 1:
                return k

        return reduce(xor, nums)