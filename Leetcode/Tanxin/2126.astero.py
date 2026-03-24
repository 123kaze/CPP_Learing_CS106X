from typing import List
class Solution:
    def asteroidsDestroyed(self, mass: int, asteroids: List[int]) -> bool:
        asteroids.sort()
        n = len(asteroids)
        if n==1:
            return mass >= asteroids[0]
        cur = 0
        for i in range(n-1):
            cur = asteroids[i]
            if  mass >= cur:    mass += cur
            if mass < asteroids[i+1]:
                return False

        return True