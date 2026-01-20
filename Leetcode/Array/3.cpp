#include <bits/stdc++.h>
using namespace std;

class Solution
{
   public:
    long long quickMul(long long x, long long y, long long m)
    {
        long long res = 1;
        while (y)
        {
            if (y & 1)
            {
                res = (res * x) % m;
            }
            y >>= 1;
            x = (x * x) % m;
        }
        return res;
    }

    long long qu(long long base, long long idx, long long mod)
    {
        long long res = 1;
        while (idx)
        {
            if (idx & 1)
            {
                res = (res * base) % mod;
            }
            idx >>= 1;  // >> 完之后要用 = 进行赋值，别忘了
            base = (base * base) % mod;
        }
        return res;
    }

    // 作者：力扣官方题解
    // 链接：https://leetcode.cn/problems/final-array-state-after-k-multiplication-operations-ii/solutions/3014793/k-ci-cheng-yun-suan-hou-de-zui-zhong-shu-74yw/
    // 来源：力扣（LeetCode）
    // 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。
    vector<int> getFinalState(vector<int>& nums, int k, int multiplier)
    {
        if (multiplier == 1) return nums;  // 不是k,是multip
        long long m = 1e9 + 7;
        int n = nums.size();
        vector<pair<long long, int>> v(n);
        for (int i = 0; i < n; i++)
        {
            v[i] = {nums[i], i};
        }
        long long mx = *max_element(nums.begin(), nums.end());
        make_heap(v.begin(), v.end(), greater<>());
        for (; k && v[0].first < mx; k--)  // 大小于写反，这里是继续条件！！
        {
            pop_heap(v.begin(), v.end(), greater<>());  // 每个函数都要传入比较器！
            v[n - 1].first *= multiplier;               // k 是次数，不是乘数
            push_heap(v.begin(), v.end(), greater<>());
        }

        sort(v.begin(), v.end());
        for (int i = 0; i < n; i++)
        {
            int t = k / n + (i < k % n);
            nums[v[i].second] = (qu(multiplier, t, m) * (v[i].first % m)) % m;
        }

        return nums;
    }
};

// class Solution {
// public:
//     long long quickMul(long long x, long long y, long long m) {
//         long long res = 1;
//         while (y) {
//             if (y & 1) {
//                 res = (res * x) % m;
//             }
//             y >>= 1;
//             x = (x * x) % m;
//         }
//         return res;
//     }

//     vector<int> getFinalState(vector<int>& nums, int k, int multiplier) {
//         if (multiplier == 1) {
//             return nums;
//         }
//         long long n = nums.size(), m = 1e9 + 7;
//         long long mx = *max_element(nums.begin(), nums.end());
//         vector<pair<long long, int>> v(n);
//         for (int i = 0; i < n; i++) {
//             v[i] = {nums[i], i};
//         }
//         make_heap(v.begin(), v.end(), greater<>());
//         for (; v[0].first < mx && k; k--) {
//             pop_heap(v.begin(), v.end(), greater<>());
//             v.back().first *= multiplier;
//             push_heap(v.begin(), v.end(), greater<>());
//         }
//         sort(v.begin(), v.end());
//         for (int i = 0; i < n; i++) {
//             int t = k / n + (i < k % n);
//             nums[v[i].second] = ((v[i].first % m) * quickMul(multiplier, t, m)) % m;
//         }
//         return nums;
//     }
// };

// 作者：力扣官方题解
// 链接：https://leetcode.cn/problems/final-array-state-after-k-multiplication-operations-ii/solutions/3014793/k-ci-cheng-yun-suan-hou-de-zui-zhong-shu-74yw/
// 来源：力扣（LeetCode）
// 著作权归作者所有。商业转载请联系作者获得授权，非商业转载请注明出处。
