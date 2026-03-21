from typing import List
from collections import defaultdict
class Solution:
    def groupAnagrams(self, strs: List[str]) -> List[List[str]]:
        dic = defaultdict(list)
        for s in strs:
            lis = [0]*26
            for c in s:
                lis[ord(c)-ord('a')] += 1
            dic[tuple(lis)].append(s)

        return list(dic.values())



