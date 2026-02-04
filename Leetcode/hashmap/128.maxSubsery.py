from typing import List

class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        maxl = 0
        ma1 =0
        curnum = 0
        s = set(nums)
        n = len(s)
        for num in s:
            if num -1 not in s:
                curnum = num
                maxl =1

                while curnum+1 in s:
                    curnum = curnum+1
                    maxl +=1
                    ma1 = max(ma1,maxl)        
        
        
        return ma1


s = Solution()
print(s.longestConsecutive([100,4,200,1,3,2]))
