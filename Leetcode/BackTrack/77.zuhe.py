def backtrack(arr,first,res,nums,k):
    if(len(nums) == k):
        res.append(nums[:])
        return
    for i in range(first,len(arr)-(k-first)+2):   # We pruning here , we need to chose k-first
    # And from i to n ,we can choose n-i+1,  so , if n -i +1 < k - first, we can purning
    # range is left and right ,so n - (k-first ) +2
        nums.append(arr[i])
        backtrack(arr,i+1,res,nums,k)
        nums.pop()
    


class Solution:
    def combine(self, n: int, k: int) -> List[List[int]]:
        arr = [x for x in range(1,n+1)]
        res = []
        nums = []
        backtrack(arr,0,res,nums,k)
        return res