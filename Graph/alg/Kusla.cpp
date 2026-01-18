#include <algorithm>
#include <iostream>
#include <vector>

using namespace std;

struct Edge
{
    int u, v, w;
    bool operator<(const Edge& other) const  // 重载小顶堆
    {
        return w < other.w;
    }
};

// 并查集查找
int find(vector<int>& parent, int i)
{
    if (parent[i] == i) return i;
    return parent[i] = find(parent, parent[i]);  // 路径压缩
}

void kruskal(int n, vector<Edge>& edges)
{
    sort(edges.begin(), edges.end());  // 1. 按边权排序

    vector<int> parent(n + 1);
    for (int i = 1; i <= n; i++) parent[i] = i;

    int mst_weight = 0;
    int edges_count = 0;

    for (auto& edge : edges)
    {
        int rootU = find(parent, edge.u);
        int rootV = find(parent, edge.v);

        // 2. 如果不在同一个集合，说明不形成环
        if (rootU != rootV)
        {
            parent[rootU] = rootV;  // 合并
            mst_weight += edge.w;
            edges_count++;
            cout << "添加边: " << edge.u << " - " << edge.v << " 权值: " << edge.w << endl;
        }
    }

    if (edges_count == n - 1)
        cout << "最小生成树总权重: " << mst_weight << endl;
    else
        cout << "图不连通，无法生成 MST" << endl;
}
