class Solution:
    def getFinalState(self, nums: List[int], k: int, multiplier: int) -> List[int]:
        if multiplier == 1:
            return nums
        n, m = len(nums), int(1e9 + 7)
        mx = max(nums)
        v = [(num, i) for i, num in enumerate(nums)]
        heapify(v)
        while v[0][0] < mx and k:
            k -= 1
            num, i = heappop(v)
            heappush(v, (num * multiplier, i))
        v.sort()
        for i in range(n):
            t = k // n + (i < k % n)
            nums[v[i][1]] = ((v[i][0] % m) * pow(multiplier, t, m)) % m
        return nums


# 作者：力扣官方题解
# 链接：https://leetcode.cn/problems/final-array-state-after-k-multiplication-operations-ii/solutions/3014793/k-ci-cheng-yun-suan-hou-de-zui-zhong-shu-74yw/
# 来源：力扣（LeetCode）
# 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。
