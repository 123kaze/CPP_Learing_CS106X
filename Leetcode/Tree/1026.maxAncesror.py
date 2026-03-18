# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def maxAncestorDiff(self, root: Optional[TreeNode]) -> int:
        res = 0

        def dfs(root, min1, max1):
            nonlocal res
            if not root:
                return (min1, max1)
            min2,max2 = dfs(root.left, min1, max1)
            min3,max3 = dfs(root.right,min1, max1)

            min1 = min(min1, min2, min3)
            max1 = max(max1, max2, max3)
            v = max(abs(max1 - root.val),abs(min1 - root.val))







