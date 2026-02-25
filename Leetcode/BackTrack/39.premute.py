from typing import List


class Solution:
    def combinationSum(self, candidates: List[int], target: int) -> List[List[int]]:
        res = []

        def backtrack(tar, cur, begin):
            if tar == 0:
                res.append(cur[:])
            if tar < 0:
                return

            for i in range(begin, len(candidates)):
                cur.append(candidates[i])
                backtrack(tar - candidates[i], cur, i)
                cur.pop()

        candidates.sort()
        backtrack(target, [], 0)
        return res
