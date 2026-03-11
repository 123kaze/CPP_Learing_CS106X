from typing import List
from collections import Counter
'''对于这种只要求找数量，和下标无关的我们直接用Counter'''
class Solution:
    def getLargestOutlier(self, nums: List[int]) -> int:
        n = len(nums)
        total = sum(nums)
        cnt = Counter(nums)

        ans = float('-inf')
        for x in nums:
            cnt[x]-=1
            if (total-x)%2 ==0 and cnt[(total-x)//2] >0:
                ans = max(ans,x)
            cnt[x]+=1
        
        return ans