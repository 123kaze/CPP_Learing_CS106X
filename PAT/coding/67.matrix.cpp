#include <bits/stdc++.h>
using namespace std;

int n;
vector<long long> m;
vector<vector<long long>> dp;
vector<vector<int>> cut;

long long dfs(int i, int j) {
    if (i == j) {
        return 0;
    }

    // 已经计算过
    if (dp[i][j] != -1) {
        return dp[i][j];
    }

    long long res = LLONG_MAX;

    for (int k = i; k < j; k++) {
        long long cost =
            dfs(i, k)
            + dfs(k + 1, j)
            + m[i - 1] * m[k] * m[j];

        if (cost < res) {
            res = cost;
            cut[i][j] = k;
        }
    }

    return dp[i][j] = res;
}

string build(int i, int j) {
    if (i == j) {
        return "M" + to_string(i);
    }

    int k = cut[i][j];

    return "(" + build(i, k) + ")x(" + build(k + 1, j) + ")";
}

int main() {
    cin >> n;

    m.resize(n + 1);
    for (int i = 0; i <= n; i++) {
        cin >> m[i];
    }

    dp.assign(n + 1, vector<long long>(n + 1, -1));
    cut.assign(n + 1, vector<int>(n + 1, 0));

    long long res = dfs(1, n);

    cout << build(1, n) << endl;
    cout << res << endl;

    return 0;
}