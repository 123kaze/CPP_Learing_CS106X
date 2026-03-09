from collections import defaultdict

class Solution:
    def maxVowels(self, s: str, k: int) -> int:
        d = defaultdict()
        d['a'] = 0
        d['e'] = 0
        d['i'] = 0
        d['o'] = 0
        d['u'] = 0
        n = len(s)
        for i in range(k):
            if s[i] in d:
                d[s[i]]+=1
        
        res = sum(d.values())

        for i in range(k,n):
            cur = 0
            if s[i] in d:
                d[s[i]]+=1
            if s[i-k] in d:
                d[s[i-k]]-=1
            cur = sum(d.values())
            res = max(cur,res)

        return res


    def maxVowels1(self, s: str, k: int) -> int:
        u = set('a,e,i,o,u')
        n = len(s)
        for i in range(k):
            if s[i] in u:
                res+=1
        cur = res
        for i in range(k,n):
            if s[i] in s:
                res+=1
            if s[i-k] in s:
                res-=1
            
            cur = max(cur,res)
            

        return cur