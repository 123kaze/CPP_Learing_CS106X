from functools import lru_cache

def solution(nums,k):
    '''
    
    '''
    n = len(nums)
    @lru_cache(None)
    def dfs(i,j):
        '''
        前i个数，分成j份
        dfs(i,j) = dfs(i-len,j)+cost(i-len,i)
        '''
        if i == 0 and j == 0:
            return 0
        if i == 0 or j == 0:
            return 9999999999
        if j>i:
            return 9999999999

        res = 999999999
        for k in range(j-1,i):
            cos = cost(nums,k,i)
            res = min(res,dfs(k,j-1)+cos)
        return res

    return dfs(n,k)

def cost(nums,i,j):
    s = sum(nums[i:j])
    return s*(s+1)/2