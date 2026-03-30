from typing import List
from collections import Counter
class Solution:
    def checkStrings(self, s1: str, s2: str) -> bool:
        n = len(s1)
        s11 = s1[::2]
        s12 = s1[1::2]
        s21 = s2[::2]
        s22 = s2[1::2]
        return Counter(s11) == Counter(s21) and Counter(s12) == Counter(s22)


s = Solution()
print(s.checkStrings("abcdba","cabdab"))


