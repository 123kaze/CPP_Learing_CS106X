#include <bits/stdc++.h>
using namespace std;

int main()
{
    int n, t;
    cin >> n >> t;
    vector<int> nums(n);
    for (int i = 0; i < n; i++)
    {
        cin >> nums[i];
    }
    set s(nums.begin(), nums.end());

    for (int i = 0; i < n; i++)
    {
        int tar = t - nums[i];
        if (tar == nums[i] && tar == t / 2)
        {
            for (int j = i + 1; j < n; j++)
            {
                if (nums[j] == nums[i])
                {
                    s.erase(nums[i]);
                    break;
                }
            }
        }
        else
        {
            auto it = s.find(tar);
            if (it != s.end())
            {
                s.erase(tar);
                s.erase(nums[i]);
            }
            else
            {
                continue;
            }
        }
    }
    for (int num : nums)
    {
        if (s.find(num) != s.end())
        {
            cout << num << " ";
        }
    }
}
// 一开始准备用集合set做，发现如果这样时间复杂度会超过
// 于是改用哈希表

// int main()
// {
//     int n, t;
//     cin >> n >> t;
//     vector<int> nums(n);
//     for (int i = 0; i < n; i++)
//     {
//         cin >> nums[i];
//     }
//     unordered_map<int, int> map;
//     vector<int> res(n);
//     for (int i = 0; i < n; i++)
//     {
//         auto tar = t - nums[i];
//         if (map.find(tar) != map.end())
//         {
//             res.push_back
//         }
//         map[nums[i]] = i;
//     }
// }