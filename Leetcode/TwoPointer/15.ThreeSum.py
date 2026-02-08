from typing import List
class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        nums.sort()
        res = []
        n = len(nums)
        for i in range(n):
            if i !=0 and nums[i] == nums[i-1]:
                continue
            target = -nums[i]
            l = i+1
            r = n-1
            while(l<r):
                if(l<r and nums[l]+nums[r] == target):
                    res.append([nums[i],nums[l],nums[r]])
                    l+=1
                    r-=1
                    while(l<r and nums[l]==nums[l-1]): l+=1
                    while(l<r and nums[r] == nums[r+1]): r-=1
                elif(l<r and nums[l]+nums[r] < target):
                    l+=1
                else:
                    r-=1
        return res
                