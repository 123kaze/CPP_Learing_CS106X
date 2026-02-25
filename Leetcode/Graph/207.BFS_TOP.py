from typing import List
from collections import deque, defaultdict


class Solution:
    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        # 构建邻接表和入度数组
        graph = defaultdict(list)
        indegree = [0] * numCourses

        for course, pre in prerequisites:
            graph[pre].append(course)
            indegree[course] += 1

        q = deque()
        for cour in range(numCourses):
            if indegree[cour] == 0:
                q.append(cour)
        count = 0
        while q:
            cur = q.popleft()
            count += 1
            for n in graph[cur]:
                indegree[n] -= 1
                if indegree[n] == 0:
                    q.append(n)

        return count == numCourses
