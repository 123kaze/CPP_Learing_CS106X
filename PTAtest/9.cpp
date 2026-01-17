#include <bits/stdc++.h>
using namespace std;

struct Point
{
    int x, y;
    Point(int a, int b) : x(a), y(b)
    {
    }
};

int main()
{
    int n, m;
    cin >> n >> m;
    vector<vector<int>> map(n, vector<int>(m));
    vector<vector<int>> dist(n, vector<int>(m, -1));
    Point start(-1, -1);

    for (int i = 0; i < n; i++)
    {
        for (int j = 0; j < m; j++)
        {
            cin >> map[i][j];
            if (map[i][j] == 3)
            {
                start.x = i;
                start.y = j;
            }
        }
    }
    int dx[4] = {-1, 1, 0, 0};
    int dy[4] = {0, 0, -1, 1};

    queue<Point> q;
    q.push(start);
    dist[start.x][start.y] = 0;

    while (!q.empty())
    {
        Point cur = q.front();
        q.pop();

        if (map[cur.x][cur.y] == 4)
        {
            cout << dist[cur.x][cur.y] << endl;
            return 0;
        }

        for (int i = 0; i < 4; i++)
        {
            int nx = cur.x + dx[i];
            int ny = cur.y + dy[i];

            if (nx >= 0 && nx < n && ny >= 0 && ny < m)
            {
                if (map[nx][ny] != 1 &&
                    dist[nx][ny] == -1)  // 还要检查是否已经访问过，不然会内存超限，无限循环
                {
                    dist[nx][ny] = dist[cur.x][cur.y] + 1;
                    q.push(Point(nx, ny));
                }
            }
        }
    }
    cout << "unreachable" << endl;
}