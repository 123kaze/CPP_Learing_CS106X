from typing import List

class Solution:
    def subarraySum(self, nums: List[int], k: int) -> int:
        '''和 TwoSum 一个做法'''
        n = len(nums)
        pre = 0
        mp = dict({0:1})
        count = 0
        for i in range(n):
            pre += nums[i]
            if mp.get(pre-k,99999) != 99999:
                count += mp[pre - k]
            
            mp[pre] = mp.get(pre,0)+1
        
        return count