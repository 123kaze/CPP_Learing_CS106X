class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        u = set()
        l = 0
        res = 0
        for i in range(len(s)):
            while s[i] in u:
                u.remove(s[l])
                l += 1
            u.add(s[i])
            res = max(res, i - l + 1)

        return res