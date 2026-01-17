// 前缀和+二分答案
#include <bits/stdc++.h>
using namespace std;

// bool check(vector<int>& nums, int l, int k, int tar)
// {
//     int h = nums.size();
//     if (nums[l + k] - nums[l] <= tar && nums[h] - nums[h - k] <= tar)
//     {
//         return true;
//     }
//     else
//         return false;
// }

bool check(vector<long long>& prefix, int l, int k, int tar)
{
    int n = prefix.size();
    // 检查索引范围
    if (l + 2 * k - 1 >= n) return false;

    // 计算前半部分的和 [l, l+k-1]
    long long sum_first;
    if (l == 0)
    {
        sum_first = prefix[l + k - 1];
    }
    else
    {
        sum_first = prefix[l + k - 1] - prefix[l - 1];
    }

    // 计算后半部分的和 [l+k, l+2k-1]
    long long sum_second = prefix[l + 2 * k - 1] - prefix[l + k - 1];

    return (sum_first <= tar && sum_second <= tar);
}

int bisect(vector<long long>& nums, int l, int tar)
{
    int h = nums.size();
    int max_possible_k = (h - l) / 2;
    if (max_possible_k == 0) return 0;

    int left = 0, right = max_possible_k;
    int ans = 0;
    while (left <= right)
    {
        int mid = left + (right - left) / 2;
        if (check(nums, l, mid, tar))
        {
            ans = mid;  // 当前mid可行，尝试更大的
            left = mid + 1;
        }
        else
        {
            right = mid - 1;
        }
    }

    return ans * 2;
}
int main()
{
    int n, s;
    cin >> n >> s;
    vector<int> nums(n);
    for (int i = 0; i < n; i++)
    {
        cin >> nums[i];
    }
    vector<long long> perfix(n);
    for (int i = 0; i < n; i++)
    {
        if (!i)
        {
            perfix[i] = nums[i];
        }
        else
        {
            perfix[i] = perfix[i - 1] + nums[i];
        }
    }

    for (int i = 0; i < n; i++)
    {
        int result = bisect(perfix, i, s);
        cout << result << "\n";
    }

    return 0;
}