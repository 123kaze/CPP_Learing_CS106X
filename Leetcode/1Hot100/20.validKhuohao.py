class Solution:
    def isValid(self, s: str) -> bool:
#         有效字符串需满足：
# 左括号必须用相同类型的右括号闭合。
# 左括号必须以正确的顺序闭合。
# 每个右括号都有一个对应的相同类型的左括号。
        stack = []
        dict = {')':'(','}':'{','[':']'}
        left = set(['(','[','{'])
        for char in s:
            if char in left:
                stack.append(char)
                continue
            elif stack and dict[char] == stack[-1]:
                stack.pop()
                continue
            else:
                return False
        
        return stack == []

