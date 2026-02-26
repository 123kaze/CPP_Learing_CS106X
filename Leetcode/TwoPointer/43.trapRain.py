from typing import List
class Solution:
    def trap(self, height: List[int]) -> int:
        contain = 0
        n = len(height)
        left = [0]*n
        right = left[:]
        left[0] = height[0]
        right[-1] = height[-1]
        for i in range(1,n):
            left[i] = max(left[i-1],height[i])
        
        for j in range(n-2,-1,-1):
            right[j] = max(right[j+1],height[j])
        
        for i in range(n):
            contain+=min(right[i]-height[i],left[i]-height[i])
            

        return contain