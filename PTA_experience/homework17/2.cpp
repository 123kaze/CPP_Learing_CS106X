#include <iostream>
#include <vector>
using namespace std;

vector<int> parent;

// 查找元素x的根节点（路径压缩）
int find(int x)
{
    if (parent[x] != x)
    {
        parent[x] = find(parent[x]);  // 路径压缩
    }
    return parent[x];
}

// 合并x和y所在的集合
void unite(int x, int y)
{
    int rootX = find(x);
    int rootY = find(y);
    if (rootX != rootY)
    {
        parent[rootY] = rootX;
    }
}

int main()
{
    int N, M;
    cin >> N >> M;

    // 初始化并查集，注意节点编号从1开始
    parent.resize(N + 1);
    for (int i = 1; i <= N; i++)
    {
        parent[i] = i;
    }

    for (int i = 0; i < M; i++)
    {
        int z, x, y;
        cin >> z >> x >> y;

        if (z == 1)
        {
            // 合并操作
            unite(x, y);
        }
        else if (z == 2)
        {
            // 查询操作
            if (find(x) == find(y))
            {
                cout << "Y" << endl;
            }
            else
            {
                cout << "N" << endl;
            }
        }
    }

    return 0;
}