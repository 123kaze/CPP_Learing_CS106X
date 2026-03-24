# Definition for a binary tree node.
class TreeNode:
    def __init__(self, val=0, left=None, right=None):
        self.val = val
        self.left = left
        self.right = right
from typing import Optional
class Solution:
    def maxPathSum(self, root: Optional[TreeNode]) -> int:
        """
        计算二叉树中的最大路径和

        路径定义为从树中任意节点出发，到达任意节点的序列。该路径至少包含一个节点，
        且不一定经过根节点。路径和是路径中各节点值的总和。

        思路：使用后序遍历（DFS）计算每个节点的贡献值，同时更新全局最大路径和。
        对于每个节点，计算以该节点为"转折点"的路径和（左子树贡献 + 右子树贡献 + 节点值），
        并更新全局最大值。

        时间复杂度：O(n)，每个节点访问一次
        空间复杂度：O(h)，递归栈深度，h为树的高度

        Args:
            root: 二叉树的根节点
        Returns:
            int: 最大路径和
        """
        if not root:
            return 0

        # 初始化结果为根节点值（至少包含一个节点）
        res = root.val

        def dfs(root: Optional[TreeNode]) -> int:
            """
            深度优先搜索，计算以当前节点为终点的最大路径贡献值
            对于每个节点，计算：
            1. 左子树的最大贡献值（如果为负则取0，表示不选择左子树）
            2. 右子树的最大贡献值（如果为负则取0，表示不选择右子树）
            3. 以当前节点为"转折点"的路径和 = 左贡献 + 右贡献 + 节点值
            4. 更新全局最大路径和

            返回的是以当前节点为终点的最大路径贡献值（只能选择左或右一边）
            Args:
                root: 当前节点
            Returns:
                int: 以当前节点为终点的最大路径贡献值
            """
            nonlocal res

            # 空节点贡献值为0
            if not root:
                return 0

            # 递归计算左右子树的最大贡献值，负贡献值取0（表示不选择该子树）
            left = max(dfs(root.left), 0)
            right = max(dfs(root.right), 0)

            # 以当前节点为"转折点"的路径和（可以同时包含左右子树）
            # 这种情况下的路径形状类似倒V：左子树 -> 当前节点 -> 右子树
            path_sum = left + right + root.val

            # 更新全局最大路径和
            res = max(res, path_sum)

            # 返回以当前节点为终点的最大贡献值（只能选择左或右一边）
            # 这是为了给父节点使用，父节点只能选择一边的路径
            return max(left, right) + root.val

        # 开始DFS遍历
        dfs(root)

        return res

    from typing import List

    def asteroidsDestroyed(self, mass: int, asteroids: List[int]) -> bool:
        """
        算法1：两阶段处理（更高效）
        1. 先吸收所有能立即吸收的小行星
        2. 对剩余不能吸收的小行星排序
        3. 尝试吸收排序后的小行星

        时间复杂度：O(n + m log m)，其中m是不能立即吸收的小行星数量
        """
        rec = []
        for a in asteroids:
            if mass >= a:
                mass += a
            else:
                rec.append(a)

        rec.sort()
        for i in rec:
            if mass >= i:
                mass += i
            else:
                return False
        return True

    def asteroidsDestroyed_slower(self, mass: int, asteroids: List[int]) -> bool:
        """
        算法2：先排序再处理（较慢）
        1. 对整个数组排序：O(n log n)
        2. 按顺序尝试吸收

        时间复杂度：O(n log n)
        """
        asteroids.sort()
        for asteroid in asteroids:
            if mass >= asteroid:
                mass += asteroid
            else:
                return False
        return True
