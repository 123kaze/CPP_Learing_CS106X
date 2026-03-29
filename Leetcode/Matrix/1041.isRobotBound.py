class Solution:
    def isRobotBounded(self, instructions: str) -> bool:
        direc = [(0,-1),(-1,0),(0,1),(1,0)]
        i,j,direcIndex = 0,0,0

        for instruction in instructions:
            if instruction == 'G':
                i += direc[direcIndex][0]
                j += direc[direcIndex][1]
            elif instruction == 'L':
                direcIndex -=1
                direcIndex %= 4
            else:
                direcIndex = (direcIndex + 1) % 4
        return direcIndex !=0 or (i == 0 and j == 0)