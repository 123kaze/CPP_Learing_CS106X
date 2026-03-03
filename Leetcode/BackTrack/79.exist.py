from typing import List


# 标准回溯+dfs，建议用这个
class Solution:
    def exist(self, board: List[List[str]], word: str) -> bool:
        m = len(board)
        n = len(board[0])
        visited = [[0] * n for _ in range(m)]
        q = len(word)
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


"""标准版bfs"""


class Solution:
    def exist(self, board: List[List[str]], word: str) -> bool:
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]

        h, w = len(board), len(board[0])
        visited = [[0 * w] for _ in range(h)]
        flag = False

        def dfs(i, j, k):
            nonlocal flag
            if k == len(word):  # 这里和上面不一样，因为这里是k为开始检查的第某个数字，
                # 而上面是检查完毕的第几个数字
                flag = True
                return
            if 0 <= i < h and 0 <= j < w and visited[i][j] == 0:
                visited[i][j] = 1
                if board[i][j] == word[k]:
                    for di, dj in directions:
                        dfs(i + di, j + dj, k + 1)
                    visited[i][j] = 0
                else:
                    return

        for i in range(h):
            for j in range(w):
                dfs(i, j, 0)

        return flag


# 作者：力扣官方题解
# 链接：https://leetcode.cn/problems/word-search/solutions/411613/dan-ci-sou-suo-by-leetcode-solution/
# 来源：力扣（LeetCode）
# 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。
