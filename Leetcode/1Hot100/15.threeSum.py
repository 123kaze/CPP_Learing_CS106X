from typing import List
class Solution:
    def threeSum(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)
        nums.sort()
        res = []
        for i,v in enumerate(nums):
            if v >0:
                break
            if i > 0 and nums[i] == nums[i-1]:
                continue
            target = -v
            left = i + 1
            right = n - 1
            while left < right:
                s = nums[left] + nums[right]
                if s == target:
                    res.append([v,nums[left], nums[right]])
                    while right > left and nums[left] == nums[left+1]:
                        left += 1
                    while left < right and nums[right] == nums[right-1]:
                        right -= 1

                    right -= 1
                    left += 1
                elif s < target:
                    left += 1
                else :
                    right -= 1
        return res

s = Solution()
nums = [2,-3,0,-2,-5,-5,-4,1,2,-2,2,0,2,-4,5,5,-10]
print(s.threeSum(nums))
