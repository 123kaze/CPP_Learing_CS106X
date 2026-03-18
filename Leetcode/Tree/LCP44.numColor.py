# Definition for a binary tree node.
class TreeNode:
    def __init__(self, x):
        self.val = x
        self.left = None
        self.right = None
class Solution:
    def numColor(self, root: TreeNode) -> int:
        res = 0
        s = set()
        def dfs(node):
            if not node:
                return
            if node.val not in s:
                s.add(node.val)
            dfs(node.left)
            dfs(node.right)

        dfs(root)
        res = len(s)

        return res




