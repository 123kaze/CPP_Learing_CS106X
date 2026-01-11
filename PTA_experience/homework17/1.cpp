// 给定结点数为 n，边数为 m 的带权无向连通图 G，所有结点编号为 1,2,⋯,n。
// 求 G 的最小生成树的边权和。
// 输入格式:

// 第一行两个正整数 n,m。

// 之后的 m
// 行，每行三个正整数ui​,vi​,wi​(1≤ui​,vi​≤n,0≤wi​≤109)，描述一条连接结点
// ui​ 和 vi​，边权为 wi​ 的边。 输出格式:

// 一个整数表示 G 的最小生成树的边权和。
// 输入样例:

// 7 12
// 1 2 9
// 1 5 2
// 1 6 3
// 2 3 5
// 2 6 7
// 3 4 6
// 3 7 3
// 4 5 6
// 4 7 2
// 5 6 3
// 5 7 6
// 6 7 1

// 输出样例:

// 16

#include <algorithm>
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

    vector<vector<pair<int, int>>> adj(n + 1);
    for (int i = 0; i < m; i++)
    {
        int u, v, w;
        cin >> u >> v >> w;
        adj[u].push_back({v, w});
        adj[v].push_back({u, w});
    }

    vector<bool> visited(n + 1, false);
    priority_queue<pair<int, int>, vector<pair<int, int>>, greater<pair<int, int>>> pq;

    // 从节点1开始
    pq.push({0, 1});
    long long total_weight = 0;
    int nodes_in_mst = 0;

    while (!pq.empty() && nodes_in_mst < n)
    {
        auto [w, u] = pq.top();
        pq.pop();

        if (visited[u]) continue;

        visited[u] = true;
        total_weight += w;
        nodes_in_mst++;

        for (auto& [v, weight] : adj[u])
        {
            if (!visited[v])
            {
                pq.push({weight, v});
            }
        }
    }

    cout << total_weight << endl;

    return 0;
}

// 这里是另外一种算法
#include <algorithm>
#include <iostream>
#include <vector>
using namespace std;

struct Edge
{
    int u, v, w;
};

vector<int> parent;

int find(int x)
{
    if (parent[x] != x)
    {
        parent[x] = find(parent[x]);
    }
    return parent[x];
}

bool unite(int x, int y)
{
    int rx = find(x), ry = find(y);
    if (rx == ry) return false;
    parent[ry] = rx;
    return true;
}

int main()
{
    int n, m;
    cin >> n >> m;

    vector<Edge> edges(m);
    for (int i = 0; i < m; i++)
    {
        cin >> edges[i].u >> edges[i].v >> edges[i].w;
    }

    // 按边权排序
    sort(edges.begin(), edges.end(), [](const Edge& a, const Edge& b) { return a.w < b.w; });

    // 初始化并查集
    parent.resize(n + 1);
    for (int i = 1; i <= n; i++)
    {
        parent[i] = i;
    }

    long long total_weight = 0;
    int edges_used = 0;

    // Kruskal算法
    for (const auto& e : edges)
    {
        if (unite(e.u, e.v))
        {
            total_weight += e.w;
            edges_used++;
            if (edges_used == n - 1) break;
        }
    }

    cout << total_weight << endl;

    return 0;
}