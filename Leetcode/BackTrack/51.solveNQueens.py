from typing import List

class Solution:
    def solveNQueens(self, n: int) -> List[List[str]]:
        """
        51. N皇后问题
        在n×n的棋盘上放置n个皇后，使得它们互不攻击
        返回所有不同的解决方案
        """
        res = []
        col = [0] * n  # col[i]表示第i行皇后所在的列
        
        # 检查位置(r,c)是否合法
        def valid(r: int, c: int) -> bool:
            """
            检查第r行第c列是否可以放置皇后
            只需要检查之前的行，因为后面的行还没放置
            """
            for R in range(r):
                C = col[R]
                # 检查对角线冲突：r+c == R+C (主对角线) 或 r-c == R-C (副对角线)
                if r + c == R + C or r - c == R - C:
                    return False
            return True
        
        def dfs(r: int, s: set) -> None:
            """
            深度优先搜索回溯
            r: 当前行
            s: 剩余可用的列集合
            """
            if r == n:  # 所有行都放置了皇后
                # 构建棋盘表示
                board = ['.' * c + 'Q' + '.' * (n - 1 - c) for c in col]
                res.append(board)
                return
            
            # 尝试当前行所有可用的列
            for c in s:
                if valid(r, c):
                    col[r] = c  # 放置皇后
                    dfs(r + 1, s - {c})  # 递归下一行，移除已使用的列
        
        # 从第0行开始，初始所有列都可用
        dfs(0, set(range(n)))
        return res

# 测试用例
if __name__ == "__main__":
    sol = Solution()
    
    # 测试n=4
    result4 = sol.solveNQueens(4)
    print(f"n=4 的解决方案数量: {len(result4)}")
    print("解决方案:")
    for i, board in enumerate(result4):
        print(f"方案 {i+1}:")
        for row in board:
            print(f"  {row}")
        print()
    
    # 测试n=1
    result1 = sol.solveNQueens(1)
    print(f"n=1 的解决方案数量: {len(result1)}")
    
    # 测试n=2 (无解)
    result2 = sol.solveNQueens(2)
    print(f"n=2 的解决方案数量: {len(result2)}")
    
    # 测试n=8 (经典8皇后问题)
    result8 = sol.solveNQueens(8)
    print(f"n=8 的解决方案数量: {len(result8)} (经典8皇后问题有92个解)")