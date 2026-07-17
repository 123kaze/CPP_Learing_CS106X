# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from functools import lru_cache
from typing import Optional
class Solution:
    def rob(self, root: Optional[TreeNode]) -> int:
        @lru_cache(None)
        def dfs(node):
            '''
            dfs(node)[yes,no] = [dfs(node.left)[no]+dfs(node.right)[no],max(dfs(node.left)[yes],dfs(node.right)[no])+
            max(dfs(node.left)[no],dfs(node.right)[yes])
            ]
            :param node:
            :return: 得到的最大的价格
            '''
            if not node:
                return 0,0

            left,nleft = dfs(node.left)
            right,nright = dfs(node.right)

            curyes = nleft + nright + node.val
            curno = max(left+nright,right+nleft,left+right,nleft+nright)

            return  curyes,curno

        l,r =  dfs(root)
        return max(l,r)