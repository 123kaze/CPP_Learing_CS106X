from typing import List

class Solution:
    def longestConsecutive(self, nums: List[int]) -> int:
        maxl = 0
        curmax = 0
        s = set(nums)
        for num in s:
            if num-1 not in s:
                curmax=1
                curnum = num
                while curnum +1 in s:
                    curmax+=1
                    curnum+=1
                
                maxl = max(curmax,maxl)

        return maxl
s = Solution()
print(s.longestConsecutive([100,4,200,1,3,2]))
