class Solution:
    def uniformArray(self, nums1: list[int]) -> bool:
        n1 = len([x for x in nums1 if x % 2 == 1])
        min_odd = min(x for x in nums1 if x % 2 == 1) if n1 >= 1 else float('inf')
        min_even = min(x for x in nums1 if x % 2 == 0) if n1 != len(nums1) else float('inf')

    # Case 1: all even in nums2
        if n1 == 0:
            return True

    # Case 2: all odd in nums2
        if n1 >= 1 and min_even > min_odd:
            return True

        return False