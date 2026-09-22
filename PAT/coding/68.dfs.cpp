#include <algorithm>
#include <iostream>
#include <vector>

using namespace std;

int n;
int capacity;
vector<int> weights;
vector<long long> values;
vector<vector<long long>> memo;

long long dfs(int i, int space) {
    if (i < 0) {
        return 0;
    }

    long long& result = memo[i][space];
    if (result != -1) {
        return result;
    }

    result = dfs(i - 1, space);
    if (space >= weights[i]) {
        result = max(result, values[i] + dfs(i - 1, space - weights[i]));
    }

    return result;
}

int main() {
    cin >> n >> capacity;

    weights.resize(n);
    values.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> weights[i];
    }
    for (int i = 0; i < n; ++i) {
        cin >> values[i];
    }

    memo.assign(n, vector<long long>(capacity + 1, -1));
    const long long best_value = dfs(n - 1, capacity);

    vector<bool> selected(n, false);
    int space = capacity;

    // Prefer selecting an item when both choices can preserve the optimum.
    for (int i = n - 1; i >= 0; --i) {
        if (space >= weights[i]
            && values[i] + dfs(i - 1, space - weights[i]) == dfs(i, space)) {
            selected[i] = true;
            space -= weights[i];
        }
    }

    cout << best_value << '\n';
    for (int i = 0; i < n; ++i) {
        cout << (selected[i] ? 1 : 0) << ' ';
    }

    return 0;
}
