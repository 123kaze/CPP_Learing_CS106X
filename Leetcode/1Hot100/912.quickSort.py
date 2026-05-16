from typing import List
import random

class Solution:
    def sortArray(self, nums: List[int]) -> List[int]:
        def quickSort(l, r):
            if l >= r:
                return
            pivot = nums[random.randint(l, r)]
            lt = l
            i = l
            gt = r
            while i <= gt:
                if nums[i] < pivot:
                    nums[lt], nums[i] = nums[i], nums[lt]
                    lt += 1
                    i += 1
                elif nums[i] > pivot:
                    nums[i], nums[gt] = nums[gt], nums[i]
                    gt -= 1
                else:
                    i += 1

            quickSort(l, lt - 1)
            quickSort(gt + 1, r)

        quickSort(0, len(nums) - 1)
        return nums
    


import random

class Solution:
    def sortArray(self, nums: list[int]) -> list[int]:
        def partition(l, r):
            # 随机选择 pivot 并交换到最后一位，防止最坏情况
            pivot_idx = random.randint(l, r)
            nums[pivot_idx], nums[r] = nums[r], nums[pivot_idx]
            
            pivot = nums[r]
            i = l  # i 指向“小于区域”的下一个待交换位置
            
            for j in range(l, r):
                if nums[j] < pivot:
                    nums[i], nums[j] = nums[j], nums[i]
                    i += 1
            
            # 最后把 pivot 换到它最终应该在的位置 i
            nums[i], nums[r] = nums[r], nums[i]
            return i

        def quickSort(l, r):
            if l < r:
                # 获取划分点
                p = partition(l, r)
                # 递归左右子数组
                quickSort(l, p - 1)
                quickSort(p + 1, r)

        quickSort(0, len(nums) - 1)
        return nums