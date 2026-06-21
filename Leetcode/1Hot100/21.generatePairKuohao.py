from typing import List

class Solution:
    def generateParenthesis(self, n: int) -> List[str]:
        t = 2*n
        res = []
        def dfs(path,q,m):
            # q 为左括号个数
            if len(path) == t:
                res.append(path[:])
                return
            if m>q:
                return
            elif m == q and q<n:
                path+='('
                dfs(path,q+1,m)
            elif q>m and q<n:
                path+='('
                dfs(path,q+1,m)
                path=path[:q+m]
                path+=')'
                dfs(path,q,m+1)
            if q==n and m<n:
                path+=')'
                dfs(path,q,m+1)
        dfs('',0,0)
        return res


from typing import List

class Solution1:
    def generateParenthesis(self, n: int) -> List[str]:
        res = []

        def dfs(path: str, left: int, right: int):
            if len(path) == 2 * n:
                res.append(path)
                return

            # 左括号还没用完，可以放左括号
            if left < n:
                dfs(path + "(", left + 1, right)

            # 右括号数量不能超过左括号
            if right < left:
                dfs(path + ")", left, right + 1)

        dfs("", 0, 0)
        return res
                

            

