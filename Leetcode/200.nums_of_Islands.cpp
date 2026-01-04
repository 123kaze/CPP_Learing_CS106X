#include <algorithm>
#include <cmath>
#include <iostream>
#include <queue>
#include <tuple>
#include <utility>
#include <vector>
using namespace std;

void mark(vector<vector<char>>& n, int i, int j)
{
    n[i][j] = '0';
    return;
}

void BFS(vector<vector<char>>& grid, int i, int j)
{
    int m = grid.size();
    int n = grid[0].size();
    vector<tuple<int, int>> directions = {make_tuple(-1, 0), make_tuple(1, 0), make_tuple(0, -1),
                                          make_tuple(0, 1)};

    queue<tuple<int, int>> q;
    q.push(make_tuple(i, j));
    mark(grid, i, j);

    while (!q.empty())
    {
        auto [a, b] = q.front();
        q.pop();

        for (auto [a1, b1] : directions)
        {
            int newX = a + a1;
            int newY = b + b1;

            if (newX >= 0 && newX < m && newY >= 0 && newY < n && grid[newX][newY] == '1')
            {
                mark(grid, newX, newY);  // 标记为已访问
                q.push(make_tuple(newX, newY));
            }
        }
    }
}

class Solution
{
   public:
    int numIslands(vector<vector<char>>& grid)
    {
        int count = 0;
        int m = grid.size();
        int n = grid[0].size();

        for (int i = 0; i < m; i++)
        {
            for (int j = 0; j < n; j++)
            {
                if (grid[i][j] == '1')
                {
                    BFS(grid, i, j);

                    count++;
                }
            }
        }
        return count;
    }
};

void DFS(vector<vector<char>>& grid, int i, int j)
{
    int m = grid.size();
    int n = grid[0].size();

    if (i < 0 || j < 0 || i >= grid.size() || j >= grid[0].size() || grid[i][j] == '0') return;

    mark(grid, i, j);

    DFS(grid, i + 1, j);
    DFS(grid, i - 1, j);
    DFS(grid, i, j + 1);
    DFS(grid, i, j - 1);
}