class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        if not s:
            return 0

        char_set = set()
        left = 0
        max_len = 0

        for right in range(len(s)):
            # 关键：当遇到重复字符时，移动左指针直到不重复
            while s[right] in char_set:
                char_set.remove(s[left])
                left += 1

            # 添加当前字符
            char_set.add(s[right])

            # 更新最大长度
            max_len = max(max_len, right - left + 1)

        return max_len


class Solution:
    def lengthOfLongestSubstring(self, s: str) -> int:
        occ = set()
        n = len(s)
        rk, ans = -1, 0

        for i in range(n):
            # 左指针右移，移除一个字符
            if i != 0:
                occ.remove(s[i - 1])

            # 右指针向右扩展，直到遇到重复
            while rk + 1 < n and s[rk + 1] not in occ:
                occ.add(s[rk + 1])
                rk += 1

            # 当前窗口长度
            ans = max(ans, rk - i + 1)

            # 关键：这里不需要重置 rk，因为 rk 只会向右移动
            # 当左指针右移时，窗口自然变小，但右指针保持当前位置
            # 只有当右指针还能继续右移时才继续移动

        return ans
