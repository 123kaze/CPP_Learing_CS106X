from typing import List


class Solution:
    def permuteUnique(self, nums: List[int]) -> List[List[int]]:
        n = len(nums)
        nums.sort()
        used = [False] * n
        res = []
        cur: list[int] = []

        def backtrack(current, n, now, nums, used):
            """
            backtrack 的 Docstring

            :param current: 说明
            :param n: 说明
            :param now: 说明
            :param nums: 说明
            :param used: 说明
            """
            if len(now) == n:
                res.append(now[:])
                return

            for i in range(n):
                if used[i] == True:
                    continue

                if i > 0 and nums[i] == nums[i - 1] and not used[i - 1]:
                    continue
                
                else:

                    used[i] = True

                    now.append(nums[i])
                    backtrack(i + 1, n, now, nums, used)
                    now.pop()
                    used[i] = False

        backtrack(0, n, cur, nums, used)
        return res


s = Solution()
nums = [1, 1, 2]
print(s.permuteUnique(nums))
