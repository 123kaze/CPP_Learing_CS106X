#include <algorithm>
#include <climits>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

int main()
{
    int n, m;
    cin >> n >> m;

    // 初始化二维向量
    vector<vector<int>> map(n, vector<int>(m));

    // 读取输入矩阵
    int total_sum = 0;
    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < m; j++)
        {
            cin >> map[i][j];
            total_sum += map[i][j];
        }
    }

    // 计算行前缀和
    vector<int> row_sum(n, 0);  // 每行的总和
    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < m; j++)
        {
            row_sum[i] += map[i][j];
        }
    }

    // 计算列前缀和
    vector<int> col_sum(m, 0);  // 每列的总和
    for (int j = 0; j < m; j++)
    {
        for (int i = 0; i < n; i++)
        {
            col_sum[j] += map[i][j];
        }
    }

    int res = INT_MAX;

    // 尝试横向切割（在第i行和第i+1行之间切割）
    int top_sum = 0;
    for (int i = 0; i < n - 1; i++)  // 最多切割到 n-2 行，因为最后一行不能切
    {
        top_sum += row_sum[i];                 // 上半部分的和
        int bottom_sum = total_sum - top_sum;  // 下半部分的和
        int diff = abs(top_sum - bottom_sum);
        res = min(res, diff);
    }

    // 尝试纵向切割（在第j列和第j+1列之间切割）
    int left_sum = 0;
    for (int j = 0; j < m - 1; j++)  // 最多切割到 m-2 列，因为最后一列不能切
    {
        left_sum += col_sum[j];                // 左半部分的和
        int right_sum = total_sum - left_sum;  // 右半部分的和
        int diff = abs(left_sum - right_sum);
        res = min(res, diff);
    }

    // 输出最小差值
    cout << res << endl;

    return 0;
}

// #include <iostream>
// #include <vector>
// #include <climits>

// using namespace std;
// int main () {
//     int n, m;
//     cin >> n >> m;
//     int sum = 0;
//     vector<vector<int>> vec(n, vector<int>(m, 0)) ;
//     for (int i = 0; i < n; i++) {
//         for (int j = 0; j < m; j++) {
//             cin >> vec[i][j];
//             sum += vec[i][j];
//         }
//     }
//     // 统计横向
//     vector<int> horizontal(n, 0);
//     for (int i = 0; i < n; i++) {
//         for (int j = 0 ; j < m; j++) {
//             horizontal[i] += vec[i][j];
//         }
//     }
//     // 统计纵向
//     vector<int> vertical(m , 0);
//     for (int j = 0; j < m; j++) {
//         for (int i = 0 ; i < n; i++) {
//             vertical[j] += vec[i][j];
//         }
//     }
//     int result = INT_MAX;
//     int horizontalCut = 0;
//     for (int i = 0 ; i < n; i++) {
//         horizontalCut += horizontal[i];
//         result = min(result, abs(sum - horizontalCut - horizontalCut));
//     }
//     int verticalCut = 0;
//     for (int j = 0; j < m; j++) {
//         verticalCut += vertical[j];
//         result = min(result, abs(sum - verticalCut - verticalCut));
//     }
//     cout << result << endl;
// }
