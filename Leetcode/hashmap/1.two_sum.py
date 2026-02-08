from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        dic = {}
        for i,num in enumerate(nums):
            curtar = target - num
            if num in dic:
                return [i,dic[num]]
            else:
                dic[curtar] = i

        
s = Solution()
print(s.twoSum([2,7,11,15],9))