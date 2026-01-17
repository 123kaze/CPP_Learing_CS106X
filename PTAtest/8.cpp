

// 可以用next_permutation()直接做
#include <bits/stdc++.h>
using namespace std;

vector<int> nums;
vector<int> path;
vector<bool> used;
int n;

void dfs()
{
    if (path.size() == n)
    {
        for (int i = 0; i < n; i++)
        {
            cout << path[i];
            if (i < n - 1) cout << " ";
        }
        cout << endl;
        return;
    }
    for (int i = 0; i < n; i++)
    {
        if (used[i]) continue;
        if (i > 0 && nums[i] == nums[i - 1] && !used[i - 1]) continue;
        used[i] = true;
        path.push_back(nums[i]);
        dfs();
        path.pop_back();
        used[i] = false;
    }
}

int main()
{
    cin >> n;
    nums.resize(n);
    used.resize(n, false);

    for (int i = 0; i < n; i++)
    {
        cin >> nums[i];
    }

    sort(nums.begin(), nums.end());  // 确保有序，便于去重
    dfs();

    return 0;
}

// #include <bits/stdc++.h>
// using namespace std;

// int main() {
//     int n;
//     cin >> n;

//     vector<int> nums(n);
//     for (int i = 0; i < n; i++) {
//         cin >> nums[i];
//     }
//     sort(nums.begin(), nums.end());

//     do {
//         for (int i = 0; i < n; i++) {
//             cout << nums[i];
//             if (i < n - 1) cout << " ";
//         }
//         cout << endl;
//     } while (next_permutation(nums.begin(), nums.end()));

//     return 0;
// }