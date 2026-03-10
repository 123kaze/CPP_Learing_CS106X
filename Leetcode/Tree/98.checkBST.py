# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

from typing import Optional
class Solution:
    def isValidBST(self, root: Optional[TreeNode]) -> bool:
        def check(root, minval, maxval):
            if not root:
                return True

            if root.val <= minval or root.val >= maxval:
                return False

            return check(root.left, minval, root.val) and check(
                root.right, root.val, maxval
            )

        return check(root, float("-inf"), float("inf"))
