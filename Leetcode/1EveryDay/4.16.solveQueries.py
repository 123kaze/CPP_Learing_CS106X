from typing import List
from collections import defaultdict
import bisect

class Solution:
    def solveQueries(self, nums: List[int], queries: List[int]) -> List[int]:
        n = len(nums)
        # 1. 预处理：记录每个值的所有索引
        d = defaultdict(list)
        for i, v in enumerate(nums):
            d[v].append(i)

        ans = []
        memo = {} # 增加缓存

        for q in queries:
            # 如果该查询索引之前算过，直接从 memo 取值
            if q in memo:
                ans.append(memo[q])
                continue

            val = nums[q]
            ind = d[val]

            if len(ind) == 1:
                res = -1
            else:
                # 2. 二分优化：找到 q 在有序索引列表 ind 中的位置
                idx_in_ind = bisect.bisect_left(ind, q)

                res = n
                # 3. 核心逻辑：最近的相同元素只可能在 ind 里的前一个或后一个
                # 使用取模处理环形边界情况（前一个或后一个）
                for offset in [-1, 1]:
                    neighbor_idx = ind[(idx_in_ind + offset) % len(ind)]
                    di = abs(neighbor_idx - q)
                    res = min(res, di, n - di)

            memo[q] = res # 存入缓存
            ans.append(res)

        return ans