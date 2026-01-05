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
    vector<vector<int>> generateMatrix(int n)
    {
        vector<vector<int>> res(n, vector<int>(n, 0));
        int k = 0, i = 0, j = 0;
        int loop = n / 2;
        int count = 1;
        int edgel = 1;
        int startx = 0, starty = 0;
        while (loop--)
        {
            i = starty;
            // 注意这里，一定要赋值在每次循环开始的时候，不然容易错
            for (j = startx; j < n - edgel; j++)
            {
                res[i][j] = count++;
            }

            for (i = starty; i < n - edgel; i++)
            {
                res[i][j] = count++;
            }

            for (; j > startx; j--)
            {
                res[i][j] = count++;
            }

            for (; i > starty; i--)
            {
                res[i][j] = count++;
            }

            startx++;
            starty++;
            edgel++;
        }

        if (n % 2 == 1)
        {
            res[n / 2][n / 2] = n * n;
        }
        return res;
    }
};