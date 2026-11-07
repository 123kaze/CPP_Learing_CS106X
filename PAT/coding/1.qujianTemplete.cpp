#include <bits/stdc++.h>
using namespace std;

using ll = long long;
const ll INF = 1LL << 60;

int n;
vector<vector<ll>> dp;
vector<vector<int>> path;

ll dfs(int i, int j) {
    // 1. 递归边界
    if (i >= j) return 0;

    // 2. 记忆化
    if (dp[i][j] != -1) {
        return dp[i][j];
    }

    // 3. 初始化答案
    ll res = INF;

    // 4. 枚举分割点
    for (int k = i; k < j; k++) {

        ll cost = dfs(i, k)
                + dfs(k + 1, j)
                + mergeCost(i, k, j);

        if (cost < res) {
            res = cost;
            path[i][j] = k;
        }
    }

    // 5. 保存并返回答案
    return dp[i][j] = res;
}