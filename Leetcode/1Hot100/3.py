class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        u = []
        cur = max1 = 0
        for c in s:
            while c in u:
                u.pop()
                continue
            u.append(c)
            cur = len(u)
            max1 = max(max1,cur)

        
        return max1

s  = Solution()
print(s.lengthOfLongestSubstring("pwwkew"))