# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def evaluateTree(self, root: Optional[TreeNode]) -> bool:
        '''
        0 flase 1 true 2 or 3 and
        :param root:
        :return:
        '''

        def dfs(root):
            if root.val ==1:
                return True
            elif root.val == 0:
                return False

            left = dfs(root.left)
            right = dfs(root.right)
            if root.val == 2:
                return left or right
            elif root.val == 3:
                return left and right

        return dfs(root)