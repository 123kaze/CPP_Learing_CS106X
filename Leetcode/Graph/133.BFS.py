from collections import deque
import heapq
from typing import Optional


class Node:
    def __init__(self, val=0, neighbors=None):
        self.val = val
        self.neighbors = neighbors if neighbors is not None else []


class Solution:
    def cloneGraph(self, node: Optional["Node"]) -> Optional["Node"]:
        if not node:
            return node

        visited = {}

        qu = deque([node])
        visited[node] = Node(node.val)

        while qu:
            current = qu.popleft()
            for ne in current.neighbors:
                if ne not in visited:
                    visited[ne] = Node(ne.val)
                    qu.append(ne)

                visited[current].neighbors.append(visited[ne])

        return visited[node]
