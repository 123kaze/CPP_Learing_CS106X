from typing import List

class Solution:
    def maxProfit(self, prices: List[int]) -> int:
        res = 0
        if not prices:
            return res
        n = len(prices)
        min1 = 1
        for _,val in enumerate(prices):
            min1 = min(min1,val)
            res = max(val - min1,res)

         

        return res