from typing import List

class Solution:
    def sortColors(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        def partition(nums, low, high):
            pivot = nums[high]
            i = low
            for j in range(low, high):
                if nums[j] < pivot:
                    nums[i], nums[j] = nums[j], nums[i]
                    i += 1
            nums[i], nums[high] = nums[high], nums[i]
            return i
        def quickSort(nums, low, high):
            if low < high:
                p = partition(nums, low, high)
                quickSort(nums, low, p - 1)
                quickSort(nums, p + 1, high)

        quickSort(nums, 0, len(nums) - 1)


def partition(nums, low, high):
    pivot = nums[high]
    i = low
    for j in range(low, high):
        if nums[j] < pivot:
            nums[i], nums[j] = nums[j], nums[i]
            i += 1
    nums[i], nums[high] = nums[high], nums[i]
    return i

q = partition([3,6,2,4,5],0,4)
print(q)