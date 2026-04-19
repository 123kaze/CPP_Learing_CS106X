from typing import List
class Solution:
    def closestTarget(self, words: List[str], target: str, startIndex: int) -> int:
        n = len(words)
        cnt = 0
        min1 = 99999999999
        for j in range(startIndex,n+startIndex):
            q = j%n
            cnt+=1
            if words[q]==target:
                min1 = min(min1,cnt-1)
                break
        cnt1 = 0
        for i in range(startIndex, startIndex-n,-1):
            q = (i+n)%n
            cnt1+=1
            if words[q]==target:
                min1 = min(min1,cnt1-1)
                break

        return min1 if min1!=99999999999 else -1


3 5


5 3 7 3 9 3

sol = Solution()
sol.closestTarget(["a","b","leetcode"],"leetcode",0)