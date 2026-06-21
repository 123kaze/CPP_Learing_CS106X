from typing import List
class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        n = len(prices)
        minl = [0]*n
        curmin = gmin = 0
        for i,v in enumerate(prices):
            if i==0:
                minl[0] = prices[0]
                continue
            minl[i] = minl[i-1] if v > minl[i-1]else v
            curmin = v - minl[i]
            gmin = max(gmin,curmin)


        return gmin

s = Solution()
print(s.maxProfit([7,1,5,3,6,4]))