from typing import  List

class Solution:
    def maximumTripletValue(self, nums: List[int]) -> int:

        n = len(nums)
        leftMax = [0]*n
        maxL = 0
        maxR = 0
        rightMax = [0]*n
        for i in range(len(nums)):
            leftMax[i] = max(leftMax[i], maxL)
            maxL = max(maxL, nums[i])
            rightMax[-i-1] = max(rightMax[-i-1], maxR)
            maxR = max(maxR, nums[-i-1])
        maxV = 0
        for i in range(1,n):
            delta = -nums[i] + leftMax[i]
            cur = delta * rightMax[i]
            maxV = max(maxV, cur)

        return maxV if maxV >=0 else 0

s = Solution()
print(s.maximumTripletValue([12,6,1,2,7]))