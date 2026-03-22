from typing import List
class Solution:
    def searchInsert(self, nums: List[int], target: int) -> int:
        l = 0
        h = len(nums)-1
        while l <= h:
            mid = l+(h-l)//2
            if nums[mid] <= target-1:
                l = mid+1
            else:
                h = mid-1
        return l

