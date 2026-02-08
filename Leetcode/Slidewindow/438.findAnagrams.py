from typing import List
class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        ''' 滑动窗口做法 '''
        coup = [0]*27
        cous = [0]*27
        n = len(p)
        m = len(s)
        if n > m:
            return []
        res = []
        for i in range(n):
            coup[ord(p[i]) - 97] +=1
            cous[ord(s[i]) - 97] +=1
        
        if coup == cous:
            res.append(0)

        for i in range(m-n):
            cous[ord(s[i]) - 97] -=1
            cous[ord(s[i+n]) - 97] +=1
            if coup == cous:
                res.append(i+1)
        
        return res
    
s = Solution()
print(s.findAnagrams("baa",'aa'))

import collections

class Solution:
    def findAnagrams(self, s: str, p: str) -> List[int]:
        ''' 哈希表标准做法 O(nmlogm) '''
        n = len(s)
        m = len(p)
        mp = collections.defaultdict(list)
        p = ''.join(sorted(p))
        for i in range(n-m+1):
            q = ''.join(sorted(s[i:i+m]))
            mp[q].append(i)
        
        return mp[p]