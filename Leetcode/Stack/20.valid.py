class Solution:
    def isValid(self, s: str) -> bool:
        stack = []
        map = {'{':'}','[':']','(':')'}
        for c in s:
            if c in map:
                stack.append(c)
            else:
                if not stack or map[stack[-1]] != c:
                    return False
                stack.pop()
        return True if not stack else False      