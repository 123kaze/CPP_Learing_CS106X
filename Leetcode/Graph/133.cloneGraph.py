# Definition for a Node.
class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


from typing import Optional


class Solution:
    def __init__(self) -> None:
        self.visited = {}

    def cloneGraph(self, node: Optional["Node"]) -> Optional["Node"]:
        """
        cloneGraph 的 Docstring

        :param self: 说明
        :param node: 说明
        :type node: Optional['Node']
        :return: 说明
        :rtype: Node | None
        """
        if not node:
            return None

        if node in self.visited:
            return self.visited[node]

        clone = Node(node.val)
        self.visited[node] = clone

        for n in node.neighbors:
            clone.neighbors.append(self.cloneGraph(n))

        return clone
