from typing import List
from collections import defaultdict

class Solution:
    def minArrivalsToDiscard(self, arrivals: List[int], w: int, m: int) -> int:
        if not arrivals:
            return 0
        n = len(arrivals)
        d = defaultdict()
        res = 0
        count = 0
        for i in range(w):
            d[arrivals[i]] = d.get(arrivals[i],0)+1
            if d[arrivals[i]] > m:
                d[arrivals[i]]-=1
                arrivals[i] = 0
                count+=1
        
        for i in range(w,n):
            d[arrivals[i]] = d.get(arrivals[i],0)+1
            d[arrivals[i-w]] = d.get(arrivals[i-w],0)-1
            if d[arrivals[i]] > m:
                d[arrivals[i]]-=1
                arrivals[i] = 0
                count+=1

        return count