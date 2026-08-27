from typing import List
from collections import Counter

class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        n = len(s)
        m = len(p)
        cntp = Counter(p)
        cnts = Counter()
        res = []

        for i in range(n):
            cnts[s[i]]+=1

            left = i-m+1
            if left<0:
                continue

            if cntp == cnts:
                res.append(left)

            cnts[s[left]]-=1

        return res