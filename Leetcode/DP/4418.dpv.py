class Solution:
    def maximumAmount(self, coins: List[List[int]]) -> int:
        @cache  # 缓存装饰器，避免重复计算 dfs 的结果（记忆化）
        def dfs(i: int, j: int, k: int) -> int:
            if i < 0 or j < 0:
                return -inf
            x = coins[i][j]
            if i == 0 and j == 0:
                return max(x, 0) if k else x
            res = max(dfs(i - 1, j, k), dfs(i, j - 1, k)) + x  # 选
            if k and x < 0:
                res = max(res, dfs(i - 1, j, k - 1), dfs(i, j - 1, k - 1))  # 不选
            return res

        ans = dfs(len(coins) - 1, len(coins[0]) - 1, 2)
        dfs.cache_clear()  # 避免超出内存限制
        return ans

# 作者：灵茶山艾府
# 链接：https://leetcode.cn/problems/maximum-amount-of-money-robot-can-earn/solutions/3045103/wang-ge-tu-dp-by-endlesscheng-g96j/
# 来源：力扣（LeetCode）
# 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。