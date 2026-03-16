from collections import defaultdict
from typing import  List
class Solution:
    def partitionLabels(self, s: str) -> List[int]:
        idx = defaultdict(int)
        start = 0
        end = 0
        for i, c in enumerate(s):
            idx[c] = i

        partition = []

        for i, c in enumerate(s):
            end = max(end, idx[c])
            if i==end:
                partition.append(end-start+1)
                start = end+1


        return partition
