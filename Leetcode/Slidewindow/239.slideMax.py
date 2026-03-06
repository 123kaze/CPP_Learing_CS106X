from typing import List
from collections import deque

class Solution:
    def maxSlidingWindow(self, nums: List[int], k: int) -> List[int]:
        q = deque()
        res = []
        if not nums:
            return []
        if k == 1:
            return nums
        for i in range(k):
            if i>0:
                if nums[i] > q[0] :
                    while q:
                        q.popleft()

            q.append(nums[i])
        res.append(q[0])
        n = len(nums)
        for i in range(k,n):
            if nums[i] > q[0] :
                while q:
                    q.popleft()

            q.append(nums[i])
            res.append(q[0])
        
        return res
        