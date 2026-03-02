from typing import List

class Solution:
    def uniquePaths(self, m: int, n: int) -> int:
        """
        62. 不同路径
        机器人从左上角到右下角的路径数（无障碍物）
        """
        # 初始化dp数组，第一行和第一列都是1
        dp = [[1 for _ in range(n)] for _ in range(m)]
        
        # 动态规划递推
        for i in range(1, m):
            for j in range(1, n):
                dp[i][j] = dp[i-1][j] + dp[i][j-1]
        
        return dp[m-1][n-1]

# 测试用例
if __name__ == "__main__":
    sol = Solution()
    
    # 测试用例1: 3x7网格
    print(f"Test 1 (3x7): {sol.uniquePaths(3, 7)}")  # 应输出28
    
    # 测试用例2: 3x2网格
    print(f"Test 2 (3x2): {sol.uniquePaths(3, 2)}")  # 应输出3
    
    # 测试用例3: 7x3网格
    print(f"Test 3 (7x3): {sol.uniquePaths(7, 3)}")  # 应输出28
    
    # 测试用例4: 1x1网格
    print(f"Test 4 (1x1): {sol.uniquePaths(1, 1)}")  # 应输出1