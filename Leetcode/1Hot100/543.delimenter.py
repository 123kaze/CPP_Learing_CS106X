# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional

class Solution:
    
    def diameterOfBinaryTree(self, root: Optional[TreeNode]) -> int:
        self.diameter = 0
        def height(node):
            if node is None:
                return 0
            left = height(node.left)
            right = height(node.right)
            self.diameter = max(self.diameter, left + right)
            return max(left,right)+1

        return self.diameter
        # res = 0
        # def dfs(node):
        #     if node is None:
        #         return
        #     nonlocal res
        #     left = height(node.left)
        #     right = height(node.right)
            
        #     cur = left+right
        #     res = max(cur,res)
        #     dfs(node.left)
        #     dfs(node.right)

        return res
        