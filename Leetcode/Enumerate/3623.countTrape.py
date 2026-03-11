from typing import List
from collections import defaultdict,Counter

class Solution:
    def countTrapezoids(self, points: List[List[int]]) -> int:
        res = 0
        c = Counter(p[1] for p in points)
        ans = s =0
        for v in c.values():
            k = v*(v-1)//2
            res+=k*s
            s+=k

        return res
