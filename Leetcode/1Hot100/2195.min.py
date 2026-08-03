from typing import List


class Solution:
    def minimalKSum(self, nums: List[int], k: int) -> int:
        s = sorted(set(nums))
        cur = 1
        res = 0

        for num in s:
            if num > cur:
                lens = num-cur
                cnt = min(k,lens)
                res += (2*cur+ cnt - 1) * cnt // 2
                k -= cnt
                if k == 0:
                    return res
            cur = max(cur,num+1)
        if k >0:
            res += (2*cur+k-1)*k //2
        return res

