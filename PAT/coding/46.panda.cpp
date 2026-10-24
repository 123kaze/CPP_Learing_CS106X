
#include <bits/stdc++.h>
using namespace std;

int tos(string s) {
    int h = stoi(s.substr(0, 2));
    int m = stoi(s.substr(3, 2));
    int se = stoi(s.substr(6, 2));
    return h * 3600 + m * 60 + se;
}

int main() {
    int n;
    cin >> n;

    vector<pair<int, int>> res;

    for (int i = 0; i < n; i++) {
        string m, q;
        cin >> m >> q;

        int st = tos(m);
        int et = tos(q);

        res.push_back({st, 1});
        res.push_back({et, 0});
    }

    sort(res.begin(), res.end(), [](auto a, auto b) {
        if (a.first == b.first)
            return a.second > b.second;
        return a.first < b.first;
    });

    int current = 0;
    int rr = 0;

    for (auto [time, curr] : res) {
        if (curr == 1) {
            current++;
            rr = max(rr, current);
        } else {
            current--;
        }
    }

    cout << rr << endl;

    return 0;
}
