import random
from typing import List
class Solution:
    def findKthLargest(self, nums: List[int], k: int) -> int:

        def quickSelect(nums,k):
            left = []
            right = []
            mid  = []
            pivot = random.choice(nums)
            for num in nums:
                if num < pivot:
                    left.append(num)
                elif num > pivot:
                    right.append(num)
                else: mid.append(num)

            if len(right) >= k:
                return quickSelect(right,k)
            if len(right) + len(mid) >= k:
                return mid[0]
            else:#if len(left) >= k - r -m
                return quickSelect(left,k-len(right)-len(mid))

        return quickSelect(nums,k)


s = Solution()
print(s.findKthLargest([3,2,1,5,6,4], 2))