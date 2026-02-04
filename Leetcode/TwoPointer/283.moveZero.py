class Solution:
    def moveZeroes(self, nums: List[int]) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        n = len(nums)
        if n == 0 or n == 1:
            return
        last = 0
        for i in range(len(nums)):
            if nums[i] == 0:
                continue
            nums[last],nums[i] = nums[i],nums[last]
            last+=1
        