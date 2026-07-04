from typing import List

class Solution:
    def mergeTwo(self,nums1:List[int],nums2:List[int]) -> List[int]:
        res = []
        n = len(nums1)
        m = len(nums2)
        i = j = 0
        while i < n and j < m:
            if nums1[i] < nums2[j]:
                res.append(nums1[i])
                i += 1
            else:
                res.append(nums2[j])
                j += 1

        while i<n:
            res.append(nums1[i])
            i += 1
        while j<m:
            res.append(nums2[j])
            j += 1

        return res

    def mergeSort(self,nums:List[int]):
        n = len(nums)
        mid = n//2
        if n<=1:
            return nums

        left = self.mergeSort(nums[:mid])
        right = self.mergeSort(nums[mid:])

        return self.mergeTwo(left,right)
