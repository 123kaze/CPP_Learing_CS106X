
#include <bits/stdc++.h>
using namespace std;

const int MAXN = 105;
int a[MAXN][MAXN];
int n;

struct Rect {
    int x1, y1, x2, y2, score;
};

// 比较两个矩形：先看得分，再看坐标字典序
bool better(Rect p, Rect q) {
    if (p.score != q.score)
        return p.score > q.score;

    return tie(p.x1, p.y1, p.x2, p.y2) <
           tie(q.x1, q.y1, q.x2, q.y2);
}

// 找到当前最高分的合法矩形
Rect findBest() {
    Rect best = {0, 0, 0, 0, 0};

    for (int x1 = 1; x1 <= n; x1++) {
        int sum[MAXN] = {0};
        bool bad[MAXN] = {false};

        for (int x2 = x1; x2 <= n; x2++) {

            // 将每一行在 [x1, x2] 的数字压缩成一个值
            for (int y = 1; y <= n; y++) {
                sum[y] += a[y][x2];

                if (a[y][x2] == 0)
                    bad[y] = true;
            }

            // 在纵向进行最大子段和计算
            int cur = 0;
            int start = 1;

            for (int y = 1; y <= n; y++) {

                // 存在黑洞，该行不能加入矩形
                if (bad[y]) {
                    cur = 0;
                    start = y + 1;
                    continue;
                }

                // 当前和不大于 0，重新开始更优
                if (cur < 0) {
                    cur = sum[y];
                    start = y;
                } else {
                    cur += sum[y];
                }

                if (cur > 0) {
                    Rect tmp = {x1, start, x2, y, cur};

                    if (better(tmp, best))
                        best = tmp;
                }
            }
        }
    }

    return best;
}

// 消除矩形，并模拟重力下落
// void eraseRect(Rect r) {
//     for (int x = r.x1; x <= r.x2; x++) {

//         // 先把矩形中的方块清除
//         for (int y = r.y1; y <= r.y2; y++)
//             a[y][x] = 0;

//         // 把该列剩余非零方块向下压紧
//         int pos = n;

//         for (int y = n; y >= 1; y--) {
//             if (a[y][x] != 0) {
//                 a[pos][x] = a[y][x];
//                 pos--;
//             }
//         }

//         // 上方剩余位置补黑洞
//         while (pos >= 1) {
//             a[pos][x] = 0;
//             pos--;
//         }
//     }
// }
void eraseRect(Rect r) {
    int h = r.y2 - r.y1 + 1;

    for (int x = r.x1; x <= r.x2; x++) {

        // 上面的方块整体向下移动 h 格
        for (int y = r.y2; y >= h + 1; y--) {
            a[y][x] = a[y - h][x];
        }

        // 顶部填充黑洞
        for (int y = 1; y <= h; y++) {
            a[y][x] = 0;
        }
    }
}
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    cin >> n;

    for (int y = 1; y <= n; y++)
        for (int x = 1; x <= n; x++)
            cin >> a[y][x];

    int total = 0;

    while (true) {
        Rect best = findBest();

        if (best.score <= 0)
            break;

        cout << "(" << best.x1 << ", " << best.y1 << ") "
             << "(" << best.x2 << ", " << best.y2 << ") "
             << best.score << '\n';

        total += best.score;

        eraseRect(best);
    }

    cout << total << '\n';

    return 0;
}
