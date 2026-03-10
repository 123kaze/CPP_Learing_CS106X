from typing import List

class Solution:
    def maxScore(self, cardPoints: List[int], k: int) -> int:
        n = len(cardPoints)  
        l = n-k
        s = sum(cardPoints)
        cur = sum(cardPoints[:l])
        min1 = cur
        if k == n:
            return s
        for i in range(l, n):
            cur += cardPoints[i] - cardPoints[i -l]
            min1 = min(min1, cur)
        s -=min1
            
        return s
    
s = Solution()
s.maxScore([1,2,3,4,5,6,1],3)