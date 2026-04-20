from typing import List
class Solution:
    def maxDistance(self, colors: List[int]) -> int:
        n = len(colors)
        if colors[0] != colors[-1]:
            return n-1
        dis = 0
        c = colors[0]
        for i in range(1, n-1):
            if c != colors[i]:
                dis = max(i,n-1-i,dis)
        return dis



class Solution:
    def maxDistance(self, colors: List[int]) -> int:
        n = len(colors)
        first = {}
        ans = 0
        for i, c in enumerate(colors):
            if c not in first and len(first) < 2:
                first[c] = i
            ans = max(ans, i - min([j for cj, j in first.items() if cj != c], default=inf))
        return ans