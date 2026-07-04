from typing import List
import sys
sys.setrecursionlimit(1000000)
# 设置为100万
class Solution:
    def partition(self,nums,low,high):
        pivot = nums[high]
        j = low
        for i in range(low,high):
            if nums[i] < pivot and j<high:
                nums[i],nums[j] = nums[j],nums[i]
                j+=1

        nums[j],nums[high] = nums[high],nums[j]
        return j



    def quickSort(self, nums: List[int],l,h):
        n = len(nums)
        if h is None:
            h = len(nums) - 1
        if l>=h:
            return
        p = self.partition(nums,l,h)
        self.quickSort(nums,l,p-1)
        self.quickSort(nums,p+1,h)


s = Solution()
nums = [0,4,6,2,1,9,8,5,7,7,9]
s.quickSort(nums,0,None)
print(nums)