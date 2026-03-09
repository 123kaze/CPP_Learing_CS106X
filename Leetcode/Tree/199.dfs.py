# Definition for a binary tree node.
from typing import Optional, List
from collections import deque


class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def rightSideView(self, root: Optional[TreeNode]) -> List[int]:
        res = []
        def dfs(node,he):
            if not node:
                return 
            if len(res) == he:
                res.append(node.val)
            dfs(node.right,he+1)
            dfs(node.left,he+1)
        
        dfs(root,0)

        return res
