
class Solution:
    def canBeEqual(self, s1: str, s2: str) -> bool:
        s11 = set(s1[::2])
        s12 = set(s1[1::2])
        s21 = set(s2[::2])
        s22 = set(s2[1::2])
        for s in s11:
            if s not in s21:
                return False
        for s in s12:
            if s not in s22:
                return False

        return True

s = Solution()
print(s.canBeEqual("fymg", "famj"))