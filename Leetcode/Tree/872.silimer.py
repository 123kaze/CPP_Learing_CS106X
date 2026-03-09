# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def leafSimilar(self, root1: Optional[TreeNode], root2: Optional[TreeNode]) -> bool:
        ans1 = []
        ans2 = []
        def dfs(root,ans):
            if not root:
                return
            if not root.left and not root.right:
                ans.append(root.val)
                return
            dfs(root.left,ans)
            dfs(root.right,ans)
        
        dfs(root1,ans1)
        dfs(root2,ans2)
        if len(ans1) != len(ans2):
            return False

        for i,num in enumerate(ans1):
            if num != ans2[i]:
                return False
        
        return True
