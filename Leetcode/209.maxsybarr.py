class Solution:
    def minSubArrayLen(self, target: int, nums: List[int]) -> int:
        sum1 = sum(nums)
        if target > sum1:
            return 0

        cur = 0
        j = 0
        leng = 9999999999
        res = 999999
        for i in range(len(nums)):
            cur = cur + nums[i]
            while cur >= target:
                leng = i - j + 1
                # sublength  外层循环是结束，内层是开始，通过不断加入，然后
                # 像一个窗口一样，划出，得到结果
                res = leng if leng < res else res
                cur -= nums[j]
                j += 1

        return res if res != 999999 else 0
