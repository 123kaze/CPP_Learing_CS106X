# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


from typing import Optional


class Solution:
    def maxDepth(self, root: Optional[TreeNode]) -> int:
        if not root:
            return 0
        l = self.maxDepth(root.left)
        r = self.maxDepth(root.right)
        return max(l, r) + 1

    def maxDepth1(self, root: Optional[TreeNode]) -> int:
        if not root:
            return 0
        ans = 0

        def f(node, cnt):
            if not node:
                return
            cnt += 1
            nonlocal ans
            ans = max(ans, cnt)
            f(root.left, cnt)
            f(root.right, cnt)

        f(root, ans)
        return ans
