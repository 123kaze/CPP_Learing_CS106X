def solve():
    st = [False]*51
    ans = 0
    for i in range(1,8):
        st[i] = True
    for i in range(50):
        for j in range(i+1,50):
            ans+=1
            if (st[i] and st[j]):
                ans-=1
    print(ans)
solve()

