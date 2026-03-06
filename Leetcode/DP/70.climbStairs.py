class Solution:
    def climbStairs(self, n: int) -> int:
        """
        70. 爬楼梯
        每次可以爬1或2级台阶，求爬到第n级台阶的方法数
        实际上是斐波那契数列问题
        """
        if n <= 1:
            return 1
            
        # dp[i]表示爬到第i级台阶的方法数
        dp = [0] * (n + 1)
        dp[0] = 1  # 爬到第0级有1种方法（不动）
        dp[1] = 1  # 爬到第1级有1种方法
        
        # 动态规划递推
        for i in range(2, n + 1):
            dp[i] = dp[i-1] + dp[i-2]
        
        return dp[n]

# 测试用例
if __name__ == "__main__":
    sol = Solution()
    
    # 测试用例1
    print(f"Test 1 (n=2): {sol.climbStairs(2)}")  # 应输出2
    
    # 测试用例2
    print(f"Test 2 (n=3): {sol.climbStairs(3)}")  # 应输出3
    
    # 测试用例3
    print(f"Test 3 (n=4): {sol.climbStairs(4)}")  # 应输出5
    
    # 测试用例4
    print(f"Test 4 (n=5): {sol.climbStairs(5)}")  # 应输出8
    
    # 测试用例5
    print(f"Test 5 (n=10): {sol.climbStairs(10)}")  # 应输出89