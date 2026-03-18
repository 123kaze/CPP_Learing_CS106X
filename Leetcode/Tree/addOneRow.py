# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from  collections import deque
from typing import Optional
class Solution:
    def addOneRow(self, root: Optional[TreeNode], val: int, depth: int) -> Optional[TreeNode]:
         curdepth = 1
         if depth == 1:
            new_root = TreeNode(val)
            new_root.left = root
            return new_root
         q = deque()
         q.append((root, curdepth))
         while q:
             n = len(q)
             for i in range(n):
                 node, curdepth = q.popleft()
                 if not node:
                     continue

                 if curdepth == depth-1:
                     newnode1 = TreeNode(val)
                     newnode2 = TreeNode(val)
                     newnode1.left = node.left
                     newnode2.right = node.right
                     node.left = newnode1
                     node.right = newnode2
                     continue
                 if node.left:
                     q.append((node.left, curdepth+1))
                 if node.right:
                     q.append((node.right, curdepth+1))
             curdepth += 1

         return root

    def addOneRow1(self, root: Optional[TreeNode], val: int, depth: int) -> Optional[TreeNode]:
        if depth == 1:
            new_root = TreeNode(val)
            new_root.left = root
            return new_root

        def dfs(node, curdepth):
            if not node:
                return

            if curdepth == depth-1:
                left = node.left
                right = node.right

                node.left = TreeNode(val)
                node.right = TreeNode(val)
                node.left.left = left
                node.right.right = right

                return
            dfs(node.left, curdepth+1)
            dfs(node.right, curdepth+1)

        dfs(root, 1)
        return root







