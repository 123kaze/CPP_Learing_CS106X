# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


from typing import Optional


class Solution:
    def flatten(self, root: Optional[TreeNode]) -> None:
        """
        Do not return anything, modify root in-place instead.
        """
        visited = []

        def dfs(root):
            if not root:
                return
            visited.append(root)

            dfs(root.left)
            dfs(root.right)

        dfs(root)
        n = len(visited)
        for i in range(1, n):
            visited[i - 1].right = visited[i]
            visited[i - 1].left = None
