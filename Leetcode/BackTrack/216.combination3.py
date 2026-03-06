class Solution:
    def combinationSum3(self, k: int, n: int) -> List[List[int]]:
        res = []
        path = []

        def dfs(i,t):
            l = k - len(path)
            if t<0 or t > (9*l - ((l-1)*l//2)):
                return
            
            if len(path) == k:
                res.append(path[:])
                return
            
            for j in range(i,10):
                path.append(j)
                dfs(j+1,t-j)
                path.pop()
            

        dfs(1, n)
        return res
