from typing import List
from collections import Counter
class Solution:
    def furthestDistanceFromOrigin(self, moves: str) -> int:
        moves1 = []
        for c in moves:
            moves1.append(c)
        cnt = Counter(moves1)
        return abs(cnt['R']-cnt['L'])+cnt['_']