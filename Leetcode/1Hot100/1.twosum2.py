from typing import List
class Solution:
    def twoSum(self, nums: List[int], target: int) -> List[int]:
        path = {}
        res = []
        i: int
        for i,v in enumerate(nums):
            req = target-v
            if req in path:
                return [i,path[req]]
            path[v] = i

        return res