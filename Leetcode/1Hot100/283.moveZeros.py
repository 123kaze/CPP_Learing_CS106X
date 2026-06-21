from typing import List
from collections import Counter
class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        c = Counter(nums)
        m = c[0]
        j = 0
        n = len(nums)
        for i in range(len(nums)):
            if nums[i]==0:
                continue
            nums[j]=nums[i]
            j+=1
        nums[:] = nums[:n-m+1]+[0 for _ in range(m)]

            
        