from typing import List
class Solution:
    def searchMatrix(self, matrix: List[List[int]], target: int) -> bool:
        n = len(matrix)

        nums = []
        for i in range(n):
            nums = nums[:]+matrix[i][:]

        l = 0
        h = len(nums)-1
        while l <= h:
            mid = l+(h-l)//2
            if nums[mid] <= target:
                if nums[mid] == target:
                    return True
                l = mid+1
            else:
                h = mid-1

        return False