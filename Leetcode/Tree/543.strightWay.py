# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right


class Solution:
    def diameterOfBinaryTree(self, root: Optional[TreeNode]) -> int:
        if not root:
            return 0
        self.dia = 0

        def depth(root):
            if not root:
                return 0

            le = depth(root.left)
            rig = depth(root.right)

            self.dia = max(le + rig, self.dia)

            return max(le, rig) + 1

        depth(root)
        return self.dia
