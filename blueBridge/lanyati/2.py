from collections import defaultdict
from email.policy import default

cnta = [0]*2027
cntb = [0]*2027
mod = 998244353
p = defaultdict(int)
def read_input_from_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        # 根据实际文件内容解析，假设第一行是 n，后面每行是一对 (a, b)
        lines = f.read().strip().split()
        # 示例：假设文件内容为 "2026" 然后 2026 行数据
        pairs = []
        for i in range(0,len(lines), 2):
            a = int(lines[i])
            b = int(lines[i+1])
            cnta[a]+=1
            cntb[b]+=1
            p[(a, b)] +=1
            pairs.append((a, b))
    return pairs

# 用法
file_path = "./test.txt"
n = 2026# 请改成你下载后的实际路径
seq = read_input_from_file(file_path)
fac = [0]*2027
fac[0] = 1
fac[1] = 1
for i in range(1, n+1):
    fac[i] = fac[i-1]*i
def solve():
    total = fac[-1]
    seq.sort(key=lambda x: x[0])
    c1,c2,c12 = 1,1,1
    for i in range(1,n):
        if seq[i][1] < seq[i-1][1]:
            c12 = 0
            break

    for j in cnta:
        c1 = c1 *fac[j] %mod
    for j in cntb:
        c2 = c2 *fac[j] %mod

    for j in p.values():
        c12 = c12 *fac[j] %mod

    res = (total -c1 - c2 + c12)%mod
    return res+mod if res < 0 else res


if __name__ == '__main__' :
    print(solve())