from typing import List


class Solution:
    def rotate(self, nums: List[int], k: int) -> None:
        """
        Do not return anything, modify nums in-place instead.
        """
        n = len(nums)
        k %= n
        if k == 0:
            return

        count = 0
        for i in range(n):
            if count >= n:
                break

            cur = i
            pre = nums[i]

            while True:
                next = (cur + k) % n
                pre, nums[next] = nums[next], pre
                cur = next
                count += 1

                if cur == i:
                    break
            