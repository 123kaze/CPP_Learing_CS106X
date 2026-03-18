from collections import Counter,defaultdict
class Solution:
    def minWindow(self, s: str, t: str) -> str:
        if not s or not t:
            return ''
        counters = Counter()
        countert = Counter(t)

        ansl,ansr = -1,len(s)
        left, right = 0, 0

        for right,char in enumerate(s):
            counters[char] += 1
            while counters >= countert:
                if right-left < ansr - ansl:
                    ansl,ansr = left,right
                counters[s[left]] -= 1
                left += 1

        return "" if ansl<0 else s[ansl:ansr]


# 高级做法 ，太牛了/(ㄒoㄒ)/~~，膜拜
from collections import Counter

class Solution:
    def minWindow(self, s: str, t: str) -> str:
        if not s or not t:
            return ''

        # 需求计数器
        need = Counter(t)
        # 窗口计数器
        window = Counter()

        # 需要满足的不同字符种类数
        required = len(need)
        # 已经满足的字符种类数
        formed = 0

        ansl, ansr = -1, len(s)
        left = 0

        for right, char in enumerate(s):
            # 将当前字符加入窗口
            window[char] += 1

            # 关键优化：判断这个字符是否刚好达到需求
            # 如果当前字符是需要的，并且数量刚好等于需求
            if char in need and window[char] == need[char]:
                formed += 1  # 满足条件的字符种类+1

            # 当所有字符都满足时（formed == required），尝试缩小窗口
            while formed == required and left <= right:
                # 更新最小窗口
                if right - left < ansr - ansl:
                    ansl, ansr = left, right

                # 缩小窗口：移除左指针字符
                window[s[left]] -= 1
                # 如果移除的字符是需要的，并且移除后数量不足需求
                if s[left] in need and window[s[left]] < need[s[left]]:
                    formed -= 1  # 满足条件的字符种类-1
                left += 1

        return "" if ansl < 0 else s[ansl:ansr + 1]