#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>
using namespace std;

class Solution
{  // 我的想法
   public:
    int totalFruit(vector<int>& fruits)
    {
        unordered_map<int, int> lastIndex;  // 水果种类 -> 最后出现位置
        int left = 0, result = 0;

        for (int right = 0; right < fruits.size(); right++)
        {
            lastIndex[fruits[right]] = right;

            if (lastIndex.size() > 2)
            {
                // 找到最早出现的水果移除
                int minIndex = right;
                for (auto& [fruit, idx] : lastIndex)
                {
                    minIndex = min(minIndex, idx);
                }
                left = minIndex + 1;
                lastIndex.erase(fruits[minIndex]);
            }

            result = max(result, right - left + 1);
        }

        return result;
    }
};

class Solution
{
   public:
    int totalFruit(vector<int>& fruits)
    {
        int result = 0;
        int fruit1 = -1, fruit2 = -1, sum1 = 0, sum2 = 0;
        // 初始化，-1表示篮子空着
        for (int l = 0, r = 0; r < fruits.size(); r++)
        {
            // 滑动窗口：l左边界，r右边界，r遍历整个数组
            if (fruit1 == fruits[r])
            {
                sum1++;  // 当前水果是第一种，增加计数
            }
            else if (fruit2 == fruits[r])
            {
                sum2++;  // 当前水果是第二种，增加计数
            }
            else
            {
                // 遇到第三种水果，需要调整窗口

                while (sum1 != 0 && sum2 != 0)
                {
                    if (fruits[l] == fruit1)
                    {
                        sum1--;  // 左边界是第一种水果，减少计数
                    }
                    else
                    {
                        sum2--;  // 左边界是第二种水果，减少计数
                    }
                    l++;  // 左边界右移，缩小窗口
                }
                // 循环直到其中一种水果数量为0

                if (sum1 == 0)
                {
                    fruit1 = fruits[r];
                    sum1 = 1;
                }
                else
                {
                    fruit2 = fruits[r];
                    sum2 = 1;
                }
            }
            result = max(result, sum1 + sum2);
            // 每次循环更新最大窗口长度
        }
        return result;
    }
};
