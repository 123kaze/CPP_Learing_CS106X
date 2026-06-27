from typing import List
class Solution:
    def firstMissingPositive(self, nums: List[int]) -> int:
        min1 = min(nums)
        max1 = max(nums)
        n = len(nums)
        for i,v in enumerate(nums):
            while 1<=nums[i]<n and nums[nums[i]-1] != nums[i]:
                nums[nums[i]-1],nums[i] = nums[i],nums[nums[i]-1]

        for i in range(1,n+1):
            if nums[i-1] != i:
                return i 
        
        return n+1
    
s = Solution()
print(s.firstMissingPositive([-1,4,2,1,9,10]))