from typing import List
from collections import defaultdict
class Solution:
    def minLength(self, nums: List[int], k: int) -> int:
        if not nums:
            return -1
        n = len(nums)
        if n ==1:
            return -1 if nums[0] < k else 1
        for num in nums:
            if num >= k:
                return 1
        d = defaultdict(int)
        res = -1
        j = 0
        s=0
        for i in range(n):
            s+=nums[i]
            d[nums[i]] = d.get(nums[i],0)+1

            while j<=i and d[nums[i]] >1:
                d[nums[j]]-=1
                s-=nums[j]
                j+=1
                
            while s >= k and j<=i:
                cur = i-j+1
                res = min(cur,res) if res !=-1 else cur
                s-=nums[j]
                d[nums[j]]-=1
                j+=1
        return res
    



class Solution:
    def minLength(self, nums: List[int], k: int) -> int:
        cnt = defaultdict(int)
        s = left = 0
        ans = inf

        for i, x in enumerate(nums):
            # 1. 入
            cnt[x] += 1
            if cnt[x] == 1:
                s += x

            while s >= k:
                # 2. 更新答案
                ans = min(ans, i - left + 1)

                # 3. 出
                out = nums[left]
                cnt[out] -= 1
                if cnt[out] == 0:
                    s -= out
                left += 1

        return ans if ans < inf else -1


s = Solution()
s.minLength([8,8],8)