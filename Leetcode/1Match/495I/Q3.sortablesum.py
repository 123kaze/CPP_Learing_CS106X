from typing import List
class Solution:
    def sortableIntegers(self, nums: list[int]) -> int:
        n = len(nums)
        in1 = []
        for k in range(n):
            if not n%k:
                in1.append(k)
        
