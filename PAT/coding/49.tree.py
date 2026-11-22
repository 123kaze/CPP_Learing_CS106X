import sys
from typing import List, Optional


class Node:
    def __init__(self, val: int) -> None:
        self.val = val
        self.left: Optional["Node"] = None
        self.right: Optional["Node"] = None


def build(il: int, ir: int, pl: int, pr: int) -> Optional[Node]:
    # 中序区间为空，说明这里没有节点。
    if il > ir:
        return None

    # 后序遍历的最后一个元素是根节点。
    root_val = poso[pr]
    root = Node(root_val)

    # 根在中序遍历中的位置，将区间分成左右子树。
    k = ino.index(root_val)
    left_size = k - il

    root.left = build(il, k - 1, pl, pl + left_size - 1)
    root.right = build(k + 1, ir, pl + left_size, pr - 1)
    return root


def dfs(root: Optional[Node], res: List[int], depth: int, left: bool) -> None:
    if root is None:
        return

    # 第一次到达这一层时，记录当前节点。
    if depth == len(res):
        res.append(root.val)

    if left:
        # 左视图：优先访问左子树。
        dfs(root.left, res, depth + 1, True)
        dfs(root.right, res, depth + 1, True)
    else:
        # 右视图：优先访问右子树。
        dfs(root.right, res, depth + 1, False)
        dfs(root.left, res, depth + 1, False)


if __name__ == "__main__":
    data = list(map(int, sys.stdin.buffer.read().split()))
    n = data[0]
    ino = data[1:n + 1]
    poso = data[n + 1:2 * n + 1]

    # 链状树的递归深度可能超过 Python 默认限制。
    sys.setrecursionlimit(max(1000, 2 * n + 10))

    root = build(0, n - 1, 0, n - 1)
    res1: List[int] = []
    res2: List[int] = []
    dfs(root, res1, 0, True)
    dfs(root, res2, 0, False)

    # 与原 C++ 保持一致：输出时跳过值为 0 的节点。
    print("R:" + "".join(f" {val}" for val in res2 if val != 0))
    print("L:" + "".join(f" {val}" for val in res1 if val != 0))
