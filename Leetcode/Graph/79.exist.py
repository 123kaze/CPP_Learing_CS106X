from typing import List


class Solution:
    def exist(self, board: List[List[str]], word: str) -> bool:
        m = len(board)
        n = len(board[0])
        visited = [[0] * n for _ in range(m)]
        q = len(word)
        t = 0
        flag = False

        def dfs(i, j, word, t):
            nonlocal flag
            if i < 0 or i >= m or j < 0 or j >= n or visited[i][j] == 1:
                return
            if board[i][j] != word[t]:
                return

            if t == q - 1:
                flag = True
                return

            visited[i][j] = 1
            dfs(i + 1, j, word, t + 1)
            dfs(i, j + 1, word, t + 1)
            dfs(i - 1, j, word, t + 1)
            dfs(i, j - 1, word, t + 1)
            visited[i][j] = 0

        for i in range(m):
            for j in range(n):
                dfs(i, j, word, 0)

        return flag
