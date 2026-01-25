#include <algorithm>
#include <cmath>
#include <iostream>
#include <vector>

using namespace std;

class Solution
{
   public:
    vector<vector<int>> permute(vector<int>& nums)
    {
        vector<vector<int>> res;
        sort(nums.begin(), nums.end());
        res.push_back(nums);
        int n = 1;
        while (next_permutation(nums.begin(), nums.end()))
        {
            res.push_back(nums);
        }
        sort(res.begin(), res.end());
        return res;
    }
};

// class Solution {
// public:
//     void backtrack(vector<vector<int>>& res, vector<int>& output, int first, int len) {
//         if (first == len) {
//             res.push_back(output);
//             return;
//         }
//         for (int i = first; i < len; ++i) {
//             swap(output[i], output[first]);
//             backtrack(res, output, first + 1, len);
//             swap(output[i], output[first]);
//         }
//     }
//     vector<vector<int>> permute(vector<int>& nums) {
//         vector<vector<int>> res;
//         backtrack(res, nums, 0, (int)nums.size());
//         return res;
//     }
// };
