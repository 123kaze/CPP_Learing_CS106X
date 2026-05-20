from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        i = j =0
        path = {}
        res = []
        n = len(nums)
        for i,v in enumerate(nums):
            need = target - v
            if need in path:
                q = path[need]
                return [q,i]
            path[v] = i

        return []