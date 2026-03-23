from typing import List
class Solution:
    def minRemovals(self, nums: List[int], target: int) -> int:
        total_xor = 0
        for x in nums:
            total_xor ^= x
        target_xor = total_xor ^ target

        if target_xor == 0:
            return 0

        # BFS 找从 0 到 target_xor 的最短路径
        # 状态：当前异或值
        # 转移：异或上任意一个 nums[i]

        # 去重
        unique_nums = list(set(nums))

        # BFS
        visited = {0: 0}  # mask -> steps
        queue = deque([0])

        while queue:
            curr = queue.popleft()
            steps = visited[curr]

            for x in unique_nums:
                nxt = curr ^ x
                if nxt == target_xor:
                    return steps + 1
                if nxt not in visited:
                    visited[nxt] = steps + 1
                    queue.append(nxt)

        return -1