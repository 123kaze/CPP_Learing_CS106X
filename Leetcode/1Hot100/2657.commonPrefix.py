from typing import List
from collections import defaultdict


class Solution:
    def findThePrefixCommonArray(self, A: List[int], B: List[int]) -> List[int]:

        n = len(A)
        res = [0] * n

        for i in range(n):
            sa = set(A[:i])
            sb = set(B[:i])
            res[i] = len(sa & sb)

        return res[:]


class Solution:
    def findThePrefixCommonArray(self, A: List[int], B: List[int]) -> List[int]:
        sa = set()
        sb = set()
        r = [len(A)]
        for i in range(len(A)):
            sa.add(A[i])
            sb.add(B[i])
            r.append(len(sa & sb))
        return r[:]
