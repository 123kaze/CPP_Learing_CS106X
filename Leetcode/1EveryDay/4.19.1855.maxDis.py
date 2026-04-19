from typing import List
from bisect import bisect_left
class Solution:
    def maxDistance(self, nums1: List[int], nums2: List[int]) -> int:
        n = len(nums1)
        m = len(nums2)
        s = set(nums2)
        res = 0
        for i,x in enumerate(nums1):
            l,h = i,m-1
            pos = -1
            while l<=h:
                mid = l+(h-l)//2
                if nums2[mid] >= x:
                    pos = mid
                    l = mid+1
                else:
                    h = mid-1

            res = max(res,pos - i) if pos != -1 else res

        return res



class Solution:
    def maxDistance(self, nums1: List[int], nums2: List[int]) -> int:
        ans = i = 0
        for j, y in enumerate(nums2):
            while i < len(nums1) and nums1[i] > y:
                i += 1
            if i == len(nums1):
                break
            ans = max(ans, j - i)
        return ans

class Solution:
    def maxDistance(self, nums1: List[int], nums2: List[int]) -> int:
        i = 0
        max_dist = 0
        n1 = len(nums1)
        for j in range(len(nums2)):
            while i < n1 and nums1[i] > nums2[j]:
                i += 1
            if i < n1:
                max_dist = max(max_dist,j-i)
        return max_dist
