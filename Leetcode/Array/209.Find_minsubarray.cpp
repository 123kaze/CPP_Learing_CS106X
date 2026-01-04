#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

class Solution
{
   public:
    int minSubArrayLen(int target, vector<int>& nums)
    {
        long length = 0;
        long sum = 0;
        int i = 0;
        int res = 999999999;
        for (int l = 0; l < nums.size(); l++)
        {
            sum += nums[l];
            while (sum >= target)  // 注意审题，这里是>=不是>
            {
                length = (l - i + 1);
                res = length < res ? length : res;
                sum -= nums[i++];
            }
        }
        return res == 999999999 ? 0 : res;
    }
};