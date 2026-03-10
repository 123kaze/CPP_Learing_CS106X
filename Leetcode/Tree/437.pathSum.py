# Definition for a binary tree curcurNode.
from typing import List,Optional

class TreecurNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
class Solution:
    def pathSum(self, root: Optional[TreecurNode], targetSum: int) -> int:
        if not root:
            return 0
            
        # 包含根节点的路径 + 不包含根节点的路径（左子树）+ 不包含根节点的路径（右子树）
        return self.dfs(root, targetSum) + \
               self.pathSum(root.left, targetSum) + \
               self.pathSum(root.right, targetSum)
    
    def dfs(self,curNode:Optional[TreecurNode],target):
            if not curNode:
                return 0
            
            count = 0
            if curNode.val == target:
                count += 1
            
            count += self.dfs(curNode.left, target - curNode.val)
            count += self.dfs(curNode.right, target - curNode.val)
            
            return count