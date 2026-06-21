from typing import List
class Solution:
    def search(self, nums: List[int], target: int) -> int:
        
        def findmin(nums):
            l = 0
            r = len(nums)-1
            while l<=r:
                mid = l + (r-l)//2
                if nums[-1] < nums[mid]:
                    l = mid+1
                else:
                    r = mid-1
            return l
        idx = findmin(nums)
        n = len(nums)
        l =0
        r = n
        def find(nums,l,r):
            while l<=r:
                mid = l+(r-l)//2
                if nums[mid] < target:
                    l = mid+1
                elif nums[mid] == target:
                    return mid    
                else:
                    r = mid-1
            return -1
            
        if nums[-1] < target:
            return find(nums,0,idx)
        else:
            return find(nums,idx,n)


    
s = Solution()
print(s.search([4,5,6,7,0,1,2],2))
