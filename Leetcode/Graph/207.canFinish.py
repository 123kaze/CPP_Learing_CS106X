from typing import List
from collections import defaultdict


class Solution:

    def canFinish(self, numCourses: int, prerequisites: List[List[int]]) -> bool:
        """
        First,we should creat a graph , key is pre because
        its a pre, esay to dfs.
        Then ,using visited list.
        DFS,so if visited == 2,its circle
        """
        graph = defaultdict(list)
        for course, pre in prerequisites:
            graph[pre].append(course)

        visited = [0] * numCourses

        def checkCircle(course):
            if visited[course] == 1:
                return True
            if visited[course] == 2:
                return False

            visited[course] = 1
            for ne in graph[course]:
                if checkCircle(ne):
                    return True

            visited[course] = 2
            return False

        for cour in range(numCourses):
            if visited[cour] == 0:
                if checkCircle(cour):
                    return False

        return True
