from typing import  List
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        midx = self.findMin(nums)
        if target > nums[-1]:
            return self.searchInsert(nums,0,midx-1, target)
        else:
            return self.searchInsert(nums,midx, len(nums)-1,target)

    def findMin(self, nums: List[int]) -> int:
        left, right = 0, len(nums)-1
        while left <= right:
            mid = left + (right-left)//2
            if nums[mid] <= nums[-1]:
                if nums[mid] == nums[-1]:
                    return mid
                right = mid-1
            else:
                left = mid+1
        return left

    def searchInsert(self, nums: List[int], l,h,target: int) -> int:
        while l <= h:
            mid = l+(h-l)//2
            if nums[mid] <= target-1:
                if nums[mid] == target:
                    return mid
                l = mid+1
            else:
                h = mid-1
        return l if nums[l] == target else -1