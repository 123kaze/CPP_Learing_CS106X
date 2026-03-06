from typing import List


class Solution:
    def generateParenthesis(self, n: int) -> List[str]:
        res = []
        if not n:
            return []

        def backTrack(stack, left, right):
            if len(stack) == 2 * n:
                res.append("".join(stack[:]))
                return
            if left < n:
                stack.append("(")
                backTrack(stack, left + 1, right)
                stack.pop()
            if right < left:
                stack.append(")")
                backTrack(stack, left, right + 1)
                stack.pop()

        backTrack([], 0, 0)
        return res
