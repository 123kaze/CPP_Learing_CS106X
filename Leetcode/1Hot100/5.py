class Solution:
    def longestPalindrome(self, s: str) -> str:
        res = {}
        n = len(s)
        max1 = 0
        for i,c in enumerate(s):
            if i == 0:
                continue
            left = right = i
            while 0<=left<=right<n and s[left] == s[right]:
                left-=1
                right+=1
            leg = right-left+1
            max1 = max(max1,leg)
            res[leg] = s[left:right] 
        
        return res[max1]
