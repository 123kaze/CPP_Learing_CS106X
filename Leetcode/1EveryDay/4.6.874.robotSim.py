from typing import List
class Solution:
    def robotSim(self, commands: List[int], obstacles: List[List[int]]) -> int:
        dire = [(-1,0),(0,1),(1,0),(0,-1)]
        px,py,d = 0,0,1
        mp = set([tuple(i) for i in obstacles])
        res = 0
        for command in commands:
            if command <0:
                d+=1 if command==-1 else -1
                d%=4
            else:
                for i in range(command):
                    if tuple([px+dire[d][0],py+dire[d][1]]) in mp:
                        break
                    px,py = px+dire[d][0],py+dire[d][1]
                    res = max(res,px*px+py*py)

        return res