# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def kthSmallest(self, root: Optional[TreeNode], k: int) -> int:
        if not root:
            return 0
        nums = []

        def trverse(root):
            if not root:
                return
            trverse(root.left)
            nums.append(root.val)
            trverse(root.right)

        trverse(root)

        return nums[k - 1]
