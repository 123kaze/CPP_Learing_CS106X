from typing import List

class Solution:
    def uniquePathsWithObstacles(self, ob: List[List[int]]) -> int:
        """
        63. 不同路径 II
        网格中有障碍物，求从左上角到右下角的路径数
        """
        if not ob or ob[0][0] == 1:
            return 0
        
        m = len(ob)
        n = len(ob[0])
        
        # 初始化dp数组
        dp = [[0 for _ in range(n)] for _ in range(m)]
        dp[0][0] = 1
        
        for i in range(m):
            for j in range(n):
                if ob[i][j] == 1:
                    dp[i][j] = 0
                    continue
                else:
                    if i > 0:
                        dp[i][j] += dp[i-1][j]
                    if j > 0:
                        dp[i][j] += dp[i][j-1]
        
        return dp[m-1][n-1]

# 测试用例
if __name__ == "__main__":
    sol = Solution()
    
    # 测试用例1: 无障碍物
    grid1 = [[0,0,0],[0,0,0],[0,0,0]]
    print(f"Test 1: {sol.uniquePathsWithObstacles(grid1)}")  # 应输出6
    
    # 测试用例2: 有障碍物
    grid2 = [[0,0,0],[0,1,0],[0,0,0]]
    print(f"Test 2: {sol.uniquePathsWithObstacles(grid2)}")  # 应输出2
    
    # 测试用例3: 起点有障碍物
    grid3 = [[1,0,0],[0,0,0],[0,0,0]]
    print(f"Test 3: {sol.uniquePathsWithObstacles(grid3)}")  # 应输出0