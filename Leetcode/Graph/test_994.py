#!/usr/bin/env python3
"""
Test cases for LeetCode 994. Rotting Oranges (BFS solution)
"""

from typing import List
from collections import deque

class Solution:
    def orangesRotting(self, grid: List[List[int]]) -> int:
        m = len(grid)
        n = len(grid[0])
        q = deque()

        for i in range(m):
            for j in range(n):
                if grid[i][j] == 2:
                    q.append((i, j))
        count = 0
        ne = len(q)
        dire = [(1, 0), (-1, 0), (0, 1), (0, -1)]
        while q:
            ne = len(q)
            haveNew = False
            for _ in range(ne):
                x, y = q.popleft()
                for dx, dy in dire:
                    if (
                        0 <= x + dx < m
                        and 0 <= y + dy < n
                        and grid[x + dx][y + dy] == 1
                    ):
                        q.append((x + dx, y + dy))
                        grid[x + dx][y + dy] = 2
                        haveNew = True
            if haveNew:
                count += 1

        for i in range(m):
            for j in range(n):
                if grid[i][j] == 1:
                    return -1

        return count


def test_oranges_rotting():
    sol = Solution()
    
    # Test case 1: Example from LeetCode
    grid1 = [[2,1,1],[1,1,0],[0,1,1]]
    expected1 = 4
    result1 = sol.orangesRotting([row[:] for row in grid1])  # copy grid
    print(f"Test 1: {result1 == expected1} (expected {expected1}, got {result1})")
    assert result1 == expected1, f"Test 1 failed: {result1} != {expected1}"
    
    # Test case 2: Impossible to rot all oranges
    grid2 = [[2,1,1],[0,1,1],[1,0,1]]
    expected2 = -1
    result2 = sol.orangesRotting([row[:] for row in grid2])
    print(f"Test 2: {result2 == expected2} (expected {expected2}, got {result2})")
    assert result2 == expected2, f"Test 2 failed: {result2} != {expected2}"
    
    # Test case 3: No fresh oranges, only rotten
    grid3 = [[0,2]]
    expected3 = 0
    result3 = sol.orangesRotting([row[:] for row in grid3])
    print(f"Test 3: {result3 == expected3} (expected {expected3}, got {result3})")
    assert result3 == expected3, f"Test 3 failed: {result3} != {expected3}"
    
    # Test case 4: No rotten oranges, only fresh
    grid4 = [[1,1]]
    expected4 = -1
    result4 = sol.orangesRotting([row[:] for row in grid4])
    print(f"Test 4: {result4 == expected4} (expected {expected4}, got {result4})")
    assert result4 == expected4, f"Test 4 failed: {result4} != {expected4}"
    
    # Test case 5: All rotten already
    grid5 = [[2,2],[2,2]]
    expected5 = 0
    result5 = sol.orangesRotting([row[:] for row in grid5])
    print(f"Test 5: {result5 == expected5} (expected {expected5}, got {result5})")
    assert result5 == expected5, f"Test 5 failed: {result5} != {expected5}"
    
    # Test case 6: Single rotten orange
    grid6 = [[2]]
    expected6 = 0
    result6 = sol.orangesRotting([row[:] for row in grid6])
    print(f"Test 6: {result6 == expected6} (expected {expected6}, got {result6})")
    assert result6 == expected6, f"Test 6 failed: {result6} != {expected6}"
    
    # Test case 7: Single fresh orange (should be impossible)
    grid7 = [[1]]
    expected7 = -1
    result7 = sol.orangesRotting([row[:] for row in grid7])
    print(f"Test 7: {result7 == expected7} (expected {expected7}, got {result7})")
    assert result7 == expected7, f"Test 7 failed: {result7} != {expected7}"
    
    # Test case 8: Larger grid
    grid8 = [
        [2,1,1,1,1],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [1,1,1,1,1],
        [1,1,1,1,1]
    ]
    expected8 = 8  # furthest distance from (0,0) to (4,4) is 8 steps
    result8 = sol.orangesRotting([row[:] for row in grid8])
    print(f"Test 8: {result8 == expected8} (expected {expected8}, got {result8})")
    assert result8 == expected8, f"Test 8 failed: {result8} != {expected8}"
    
    # Test case 9: Multiple rotten sources
    grid9 = [[2,0,1,1,2]]
    expected9 = 2  # both rotten oranges infect adjacent fresh ones in 1 minute
    result9 = sol.orangesRotting([row[:] for row in grid9])
    print(f"Test 9: {result9 == expected9} (expected {expected9}, got {result9})")
    assert result9 == expected9, f"Test 9 failed: {result9} != {expected9}"
    
    # Test case 10: Empty cell blocks
    grid10 = [
        [2,0,1],
        [0,1,1],
        [1,1,1]
    ]
    expected10 = -1  # top-right fresh orange cannot be reached
    result10 = sol.orangesRotting([row[:] for row in grid10])
    print(f"Test 10: {result10 == expected10} (expected {expected10}, got {result10})")
    assert result10 == expected10, f"Test 10 failed: {result10} != {expected10}"
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_oranges_rotting()
