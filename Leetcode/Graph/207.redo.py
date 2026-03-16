from typing import List
from collections import deque, defaultdict


class Solution:
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        graph = defaultdict(list)
        indegrees = [0]*numCourses
        for a, b in prerequisites:
            graph[b].append(a)
            indegrees[a] += 1

        q = deque()
        for i in range(numCourses):
            if indegrees[i] == 0:
                q.append(i)

        while q:
            cur = q.popleft()
            for n in graph[cur]:
                indegrees[n] -= 1
                if indegrees[n] == 0:
                    q.append(n)

        for i in range(numCourses):
            if indegrees[i] != 0:
                return False

        return True
