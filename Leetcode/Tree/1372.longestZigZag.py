# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def longestZigZag(self, root: Optional[TreeNode]) -> int:
        res = 0
        flag = True  # True left ,flase right，当前是通过flag得到
        length = 0

        def dfs(root,flag,length):
            nonlocal res
            if not root:
                return
            res = max(res,length)
            if flag:
                dfs(root.left,flag,1)
                dfs(root.right,not flag,length+1)
            else:
                dfs(root.left,not flag,length+1)
                dfs(root.right,flag,1)
        dfs(root.left,flag,1)
        dfs(root.right,not flag,1)
        return res


s = Solution()
root = TreeNode(1)
print(s.longestZigZag(root))