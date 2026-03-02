from typing import List

class Solution:
    def minCostClimbingStairs(self, cost: List[int]) -> int:
        """
        746. 使用最小花费爬楼梯
        每次可以爬1或2级台阶，cost[i]表示爬第i级台阶的费用
        求爬到顶部的最小花费
        """
        n = len(cost)
        
        # dp[i]表示到达第i级台阶的最小花费
        dp = [0] * (n + 1)
        
        # 初始条件：从第0级或第1级开始不需要花费
        dp[0], dp[1] = 0, 0
        
        # 动态规划递推
        for i in range(2, n + 1):
            dp[i] = min(dp[i-1] + cost[i-1], dp[i-2] + cost[i-2])
        
        return dp[n]

# 测试用例
if __name__ == "__main__":
    sol = Solution()
    
    # 测试用例1
    cost1 = [10, 15, 20]
    print(f"Test 1: {sol.minCostClimbingStairs(cost1)}")  # 应输出15
    
    # 测试用例2
    cost2 = [1, 100, 1, 1, 1, 100, 1, 1, 100, 1]
    print(f"Test 2: {sol.minCostClimbingStairs(cost2)}")  # 应输出6
    
    # 测试用例3
    cost3 = [0, 0, 0, 0]
    print(f"Test 3: {sol.minCostClimbingStairs(cost3)}")  # 应输出0
    
    # 测试用例4
    cost4 = [1, 2]
    print(f"Test 4: {sol.minCostClimbingStairs(cost4)}")  # 应输出1