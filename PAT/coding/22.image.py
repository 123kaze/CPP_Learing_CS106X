n,m = map(int,input().split())

image = []
for i in range(n):
    image.append(list(map(int,input().split())))
res = [row[:] for row in image]
for i in range(1,n-1):
    for j in range(1,m-1):
        res1 = (
            image[i][j]+image[i-1][j]+image[i+1][j]+
            image[i][j-1]+image[i][j+1]
        )
        res[i][j] = (res1+2)//5
for re in res:
    print(*re,end = ' \n')
    