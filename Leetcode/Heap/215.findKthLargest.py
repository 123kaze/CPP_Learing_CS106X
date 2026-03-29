import random
from typing import List
import heapq
class Solution:
    def findKthLargest(self, nums: List[int], k: int) -> int:

        # using heap:
        # num = heapq.nlargest(k,nums)
        # return num[-1]

        def quick_select(nums,k):
            pivot = random.choice(nums)
            left = []
            right = []
            mid = []

            for num in nums:
                if num<pivot:
                    left.append(num)
                elif num == pivot:
                    mid.append(num)
                else:
                    right.append(num)


            if len(right)>=k:
                return quick_select(right,k)
            elif len(right) +len(mid) >=k:
                return pivot
            else:
                return quick_select(left,k-len(right)-len(mid))

        return quick_select(nums,k)

