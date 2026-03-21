# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
from collections import deque
class Solution:
    def addOneRow(self, root: Optional[TreeNode], val: int, depth: int) -> Optional[TreeNode]:
        q = deque()
        curdepth = 1
        q.appendleft((root, curdepth))
        if depth == 1:
            node = TreeNode(val)
            node.left = root
            return node
        while q:
            n = len(q)
            for i in range(n):
                node, curdepth = q.pop()
                if curdepth == depth-1:
                    newLeaf = TreeNode(val)
                    newLeaf.left = node.left
                    node.left = newLeaf
                    newRight = TreeNode(val)
                    newRight.right = node.right
                    node.right = newRight
                    continue
                if node.left:
                    q.appendleft((node.left, curdepth+1))
                if node.right:
                    q.appendleft((node.right, curdepth+1))

        return root

    def addOneRow1(self, root: TreeNode, val: int, depth: int) -> TreeNode:
        if root == None:
            return
        if depth == 1:
            return TreeNode(val, root, None)
        if depth == 2:
            root.left = TreeNode(val, root.left, None)
            root.right = TreeNode(val, None, root.right)
        else:
            root.left = self.addOneRow(root.left, val, depth - 1)
            root.right = self.addOneRow(root.right, val, depth - 1)
        return root



