# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def isValidBST(self, root: Optional[TreeNode] ,left = float('-inf'),right = float('inf')) -> bool:
        if not root:
            return True

        x = root.val
        return left < x < right and self.isValidBST(root.left,left,x) and self.isValidBST(root.right,x,right)