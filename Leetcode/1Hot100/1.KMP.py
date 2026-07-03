def build_next(pattern: str) -> list[int]:
    """
    next[i] 表示 pattern[0...i] 这一段中，
    最长相同真前缀和真后缀的长度
    """
    n = len(pattern)
    nxt = [0] * n

    j = 0  # 当前已经匹配的前缀长度

    for i in range(1, n):
        # 如果 pattern[i] 和 pattern[j] 不匹配，就回退 j
        while j > 0 and pattern[i] != pattern[j]:
            j = nxt[j - 1]

        # 如果匹配，说明最长前后缀长度可以加 1
        if pattern[i] == pattern[j]:
            j += 1

        nxt[i] = j

    return nxt


def kmp_search(text: str, pattern: str) -> int:
    """
    在 text 中查找 pattern 第一次出现的位置
    找不到返回 -1
    """
    if not pattern:
        return 0

    nxt = build_next(pattern)
    j = 0  # pattern 当前匹配到的位置

    for i in range(len(text)):
        # text[i] 和 pattern[j] 不匹配，pattern 回退
        while j > 0 and text[i] != pattern[j]:
            j = nxt[j - 1]

        # 匹配成功，pattern 往后走
        if text[i] == pattern[j]:
            j += 1

        # pattern 全部匹配成功
        if j == len(pattern):
            return i - len(pattern) + 1

    return -1


text = "abbaabbaaba"
pattern = "abbaaba"


print(kmp_search(text, pattern))



def parts(s):
    n = len(s)
    nxt = [0]*n

    j = 0
    for i in range(1,n):
        while j>0 and s[i] != s[j]:
            j = nxt[j-1]


        if s[i] == s[j]:
            j +=1
        nxt[i] = j

    return nxt

def pipei(text,part):
    if not part:
        return 0
    nxt = parts(part)
    j = 0
    n = len(text)
    p = len(part)
    for i in range(n):
        while j>0 and text[i] != part[j]:
            j = nxt[j-1]
        
        if text[i] == part[j]:
            j+=1
        
        if j == p:
            return i-p+1
    
    return -1

print(parts(pattern))
print(pipei(text=text,part=pattern))