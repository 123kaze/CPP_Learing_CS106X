#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    int total_minutes;
    cin >> n >> total_minutes;

    vector<int> minutes(n);
    vector<int> coins(n);
    for (int i = 0; i < n; ++i) {
        cin >> minutes[i];
    }
    for (int i = 0; i < n; ++i) {
        cin >> coins[i];
    }

    const int max_coins = accumulate(coins.begin(), coins.end(), 0);
    const int impossible = total_minutes + 1;
    vector<int> min_time(max_coins + 1, impossible);
    min_time[0] = 0;

    int reachable_coins = 0;
    for (int i = 0; i < n; ++i) {
        for (int value = reachable_coins + coins[i]; value >= coins[i]; --value) {
            min_time[value] = min(
                min_time[value],
                min_time[value - coins[i]] + minutes[i]);
        }
        reachable_coins += coins[i];
    }

    for (int value = max_coins; value >= 0; --value) {
        if (min_time[value] <= total_minutes) {
            cout << value << '\n';
            return 0;
        }
    }

    return 0;
}
