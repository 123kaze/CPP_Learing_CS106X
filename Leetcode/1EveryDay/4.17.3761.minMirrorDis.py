from typing import List
class Solution:
    def minMirrorPairDistance(self, nums: List[int]) -> int:
        res = inf
        n = len(nums)
        revn = []
        last_ind = {}
        for i in range(n):
            revn.append(int(str(nums[i])[::-1]))
        # 0 == nums[j] - revn[i]
        for j , x in enumerate(nums):
            if x in last_ind:
                res = min(res, j - last_ind[x])

            last_ind[revn[j]] = j

        return res if res < inf else -1