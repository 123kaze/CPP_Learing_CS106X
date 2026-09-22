#include <algorithm>
#include <vector>
#include <iostream>
using namespace std;

int main() {
    int n, w;
    cin >> n >> w;

    vector<int> wi(n), v(n);

    for (int i = 0; i < n; i++) {
        cin >> wi[i];
    }

    for (int i = 0; i < n; i++) {
        cin >> v[i];
    }

    vector<vector<long long>> dp(
        n + 1,
        vector<long long>(w + 1, 0)
    );

    for (int i = 1; i <= n; i++) {
        int weight = wi[i - 1];
        int value = v[i - 1];

        // 当前物品放不下
        for (int space = 0; space < weight && space <= w; space++) {
            dp[i][space] = dp[i - 1][space];
        }

        // 当前物品能放下
        for (int space = weight; space <= w; space++) {
            long long no_choose = dp[i - 1][space];
            long long choose =
                dp[i - 1][space - weight] + value;

            dp[i][space] = max(no_choose, choose);
        }
    }

    long long q = dp[n][w];

    // 恢复具体选择方案
    vector<int> ans(n, 0);

    int space = w;

    for (int i = n; i >= 1; i--) {
        int weight = wi[i - 1];
        int value = v[i - 1];

        if (
            space >= weight &&
            dp[i][space] ==
            dp[i - 1][space - weight] + value
        ) {
            ans[i - 1] = 1;
            space -= weight;
        }
    }

    cout << q << '\n';

    for (int i = 0; i < n; i++) {
        if (i > 0) cout << ' ';
        cout << ans[i];
    }

    cout << '\n';

    return 0;
}