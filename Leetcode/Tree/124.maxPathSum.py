# Definition for a binary tree node.
from collections import defaultdict
from typing import Optional

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
class Solution:
    def maxPathSum(self, root: Optional[TreeNode]) -> int:
        if not root:
            return 0
        res = root.val
        def dfs(node: Optional[TreeNode]):
            nonlocal res
            if node is None:
                return 0
            left = max(dfs(node.left),0)
            right = max(dfs(node.right),0)
            val = left+right + node.val
            res = max(res,val)
            return node.val + max(left,right)
        dfs(root)

        return res