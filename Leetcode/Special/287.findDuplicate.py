from typing import List

class Solution:
    def findDuplicate(self, nums: List[int]) -> int:
        slow = fast = 0
        while 1:
            slow = nums[slow]
            fast = nums[nums[fast]]
            if slow == fast:
                break

        head = 0
        while slow != head:
            slow = nums[slow]
            head = nums[head]
            if slow == head:
                break
        return head
                                                   45
