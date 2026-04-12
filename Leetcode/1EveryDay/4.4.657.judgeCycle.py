class Solution:
    def judgeCircle(self, moves: str) -> bool:
        res = 0
        for m in moves:
            if m == 'L':
                res += 1
            elif m == 'R':
                res -=1
            elif m == 'U':
                res+=0.1
            elif m == 'D':
                res-=0.1

        return res == 0

class Solution:
    def judgeCircle(self, moves: str) -> bool:
        return moves.count('R') == moves.count('L') and \
            moves.count('U') == moves.count('D')


s = Solution()
s.judgeCircle("RLUURDDDLU")