# Definition for a binary tree node.
from typing import List,Optional

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right

class Solution:
    def pathSum(self, root: Optional[TreeNode], targetSum: int) -> int:
        res = 0

        def dfs(target: int, curNode: Optional[TreeNode], must_include: bool):
            nonlocal res
            if not curNode:
                return
            
            if must_include:
                # 必须包含当前节点的情况
                if target == curNode.val:
                    res += 1
                # 继续向下找，必须包含子节点
                dfs(target - curNode.val, curNode.left, True)
                dfs(target - curNode.val, curNode.right, True)
            else:
                # 可以不包含当前节点的情况
                # 两种选择：
                # 1. 包含当前节点（变为must_include=True）
                dfs(target, curNode, True)
                # 2. 不包含当前节点，继续在子树中找
                dfs(target, curNode.left, False)
                dfs(target, curNode.right, False)
        
        dfs(targetSum, root, False)
        return res





# Definition for a binary tree node.
from typing import List,Optional

class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
class Solution:
    def pathSum(self, root: Optional[TreeNode], targetSum: int) -> int:
        res = 0

        def dfs(target,curNode:Optional[TreeNode]):
            nonlocal res
            if target == 0 :
                res+=1
                return
            if not curNode:
                return
    
            val = curNode.val
            dfs(target-val,curNode.left)
            dfs(target-val,curNode.right)
            dfs(target,curNode.left)
            dfs(target,curNode.right)
        
        dfs(targetSum,root)

        return res