import heapq
from typing import List
from collections import deque
class Solution:
    def maxSlidingWindow(self, nums: List[int], k: int) -> List[int]:
        if not nums:
            return []
        n = len(nums)
        he = [(-nums[i],i) for i in range(k)]
        heapq.heapify(he)
        res = [-he[0][0]]
        
        for i in range(k,n):
            heapq.heappush(he,(-nums[i],i))

            while he[0][1] <= i - k:
                heapq.heappop(he)

            res.append(-he[0][0])
            
        return res
    
    def maxSlidingWindow1(self, nums: List[int], k: int) -> List[int]:
        res = []
        q = deque()
        if not nums:
            return []
        n = len(nums)
        for i in range(k):
            while q and q[-1] < nums[i]:
                q.pop()
            q.append(nums[i])
        res.append(q[0])
        for i in range(k,n):
            if q[0] == nums[i-k]:
                q.popleft()
            while q and q[-1] < nums[i]:
                q.pop()
            q.append(nums[i])
            res.append(q[0])

        return res