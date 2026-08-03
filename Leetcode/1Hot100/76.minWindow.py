from typing import List
from collections import Counter

class Solution:
    def minWindow(self, s: str, t: str) -> str:
        s_counter = Counter(t)
        t_counter = Counter()

        leftbegin = -1
        left = 0
        right = len(s)
        for r,c in enumerate(s):
            t_counter[c]+=1
            while t_counter>=s_counter:
                if r-left < right-leftbegin:
                    right,leftbegin = r,left
                t_counter[s[left]]-=1
                left+=1

        return "" if leftbegin<0 else s[leftbegin:right+1]
