
#include <bits/stdc++.h>
using namespace std;

vector<vector<int>> g;
vector<bool> visited;
vector<int> path;
unordered_set<long long> bad;
int n;

bool dfs(int node) {
    if (path.size() == n) {
        return find(g[node].begin(), g[node].end(), 1)
               != g[node].end();
    }

    // 计算当前访问状态
    long long mask = 0;
    for (int i = 1; i <= n; i++) {
        if (visited[i]) {
            mask |= 1LL << (i - 1);
        }
    }

    // 当前球队 + 已访问球队集合
    long long state = (mask << 5) | node;

    // 这个状态之前已经证明无解
    if (bad.count(state)) {
        return false;
    }

    for (auto child : g[node]) {
        if (child == 0) continue;
        if (visited[child]) continue;

        visited[child] = true;
        path.push_back(child);

        if (dfs(child)) {
            return true;
        }

        visited[child] = false;
        path.pop_back();
    }

    // 记录失败状态
    bad.insert(state);
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    g.assign(n + 1, vector<int>(n + 1, 0));
    visited.assign(n + 1, false);

    for (int i = 1; i <= n; i++) {
        for (int j = 1; j <= n; j++) {
            char s;
            cin >> s;

            if (s == 'W') {
                g[i][j] = j;
            }
            if (s == 'L') {
                g[j][i] = i;
            }
        }
    }

    visited[1] = true;
    path.push_back(1);

    if (dfs(1)) {
        for (int i = 0; i < n; i++) {
            if (i) cout << " ";
            cout << path[i];
        }
        cout << "\n";
    } else {
        cout << "No Solution\n";
    }

    return 0;
}
