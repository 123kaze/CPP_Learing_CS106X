class Solution:
    def decodeString(self, s: str) -> str:
        sl = s
        stack = []
        res = ''
        for c in sl:
            if c != ']':
                stack.append(c)
            else:
                str = ''
                while stack and stack[-1] != '[':
                    str = stack.pop()+str

                stack.pop()
                num =''
                while stack and stack[-1].isdigit():
                    num = stack.pop()+num
                if num.isdigit():
                    stack.append(int(num)*str)
                else:
                    stack.append(str)
        return ''.join(stack)