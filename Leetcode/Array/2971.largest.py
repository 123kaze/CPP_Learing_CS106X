from typing import List

class Solution:
    def largestPerimeter(self, nums: List[int]) -> int:
        k = len(nums)
        if k < 3:
            return -1
        sum = 0
        nums.sort()
        prefix = [0]*k
        for i in range(k):
            if i == 0:
                prefix[i] = nums[i]
            else:
                prefix[i] = prefix[i-1] + nums[i]

        for i in range(2,k):
            if prefix[i-1] <= nums[i]:
                continue
            sum = prefix[i]
        return sum if sum != 0 else -1

s = Solution()
s.largestPerimeter([1,12,1,2,5,50,3])




class Solution:
    def largestPerimeter(self, nums: List[int]) -> int:
        nums.sort()
        ans = -1
        s = 0
        for x in nums:
            s += x
            if s > x * 2:  # s-x > x
                ans = s
        return ans

