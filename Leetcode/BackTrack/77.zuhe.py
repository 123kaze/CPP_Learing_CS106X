def backtrack(arr,first,res,nums,k):
    if(len(nums) == k):
        res.append(nums[:])
        return
    for i in range(first,len(arr)):
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