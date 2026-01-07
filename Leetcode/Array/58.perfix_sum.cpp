#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

int main()
{
    int n;
    cin >> n;
    int i = 0, j = 0;
    int a, b;
    vector<int> fix(n);
    for (; i < n; i++)
    {
        scanf("%d", &j);
        if (i)
            fix[i] = fix[i - 1] + j;
        else
            fix[i] = j;
    }

    while (~scanf("%d%d", &a, &b))  // 在进行大量数据的时候，用scaf和printf可以显著降低时间
    {
        int sum;
        if (!a)
            printf("%d\n", fix[b]);
        else
            printf("%d\n", fix[b] - fix[a - 1]);
    }
}