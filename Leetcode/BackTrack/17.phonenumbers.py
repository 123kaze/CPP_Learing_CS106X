from typing import List


class Solution:
    def letterCombinations(self, digits: str) -> List[str]:
        res = []
        if not digits:
            return []
        phoneMap = {
            "2": "abc",
            "3": "def",
            "4": "ghi",
            "5": "jkl",
            "6": "mno",
            "7": "pqrs",
            "8": "tuv",
            "9": "wxyz",
        }
        n = len(digits)
        cur = []

        def backTrack(idx):
            if idx == n:
                res.append("".join(cur[:]))
                return
            curnum = digits[idx]
            for char in phoneMap[curnum]:
                cur.append(char)
                backTrack(idx + 1)
                cur.pop()

        backTrack(0)
        return res
