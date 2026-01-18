#include <algorithm>
#include <iostream>
#include <vector>
using namespace std;

struct Edge
{
    int u, v;
    long long w;  // 注意：边权可能达到10^9，用long long
    Edge(int a, int b, long long c) : u(a), v(b), w(c)
    {
    }
};

// 按边权从小到大排序
bool cmp(const Edge& a, const Edge& b)
{
    return a.w < b.w;
}
// 这里是用的堆排序，所以必须用cmp

// 并查集
vector<int> parent;

int find(int x)
{
    if (parent[x] != x)
    {
        parent[x] = find(parent[x]);  // 路径压缩
    }
    return parent[x];
}

bool unionSet(int x, int y)
{
    int rootX = find(x);
    int rootY = find(y);
    if (rootX == rootY) return false;  // 已在同一连通分量
    parent[rootX] = rootY;
    return true;
}

int main()
{
    int n, m;
    cin >> n >> m;

    vector<Edge> edges;
    for (int i = 0; i < m; i++)
    {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        edges.push_back(Edge(u, v, w));
    }

    // 按边权排序
    sort(edges.begin(), edges.end(), cmp);

    // 初始化并查集
    parent.resize(n + 1);
    for (int i = 1; i <= n; i++)
    {
        parent[i] = i;
    }

    long long totalWeight = 0;
    int edgeCount = 0;

    // Kruskal算法
    for (const auto& edge : edges)
    {
        if (unionSet(edge.u, edge.v))
        {
            totalWeight += edge.w;
            edgeCount++;
            if (edgeCount == n - 1) break;  // 已经找到n-1条边，形成生成树
        }
    }

    // 检查是否连通
    if (edgeCount == n - 1)
    {
        cout << totalWeight << endl;
    }
    else
    {
        // 理论上题目保证连通，这里做保险
        cout << "Graph is not connected" << endl;
    }

    return 0;
}

// #include <iostream>
// #include <vector>
// #include <queue>
// #include <climits>
// using namespace std;

// typedef pair<long long, int> PII;  // (边权, 顶点)

// int main() {
//     int n, m;
//     cin >> n >> m;

//     vector<vector<PII>> graph(n + 1);

//     for (int i = 0; i < m; i++) {
//         int u, v;
//         long long w;
//         cin >> u >> v >> w;
//         graph[u].push_back({w, v});
//         graph[v].push_back({w, u});
//     }

//     // Prim算法
//     vector<bool> visited(n + 1, false);
//     vector<long long> dist(n + 1, LLONG_MAX);  // 存储到MST的最小边权

//     // 从节点1开始
//     dist[1] = 0;
//     long long totalWeight = 0;

//     // 最小堆
//     priority_queue<PII, vector<PII>, greater<PII>> pq;
//     pq.push({0, 1});

//     while (!pq.empty()) {
//         auto [weight, node] = pq.top();
//         pq.pop();

//         if (visited[node]) continue;

//         visited[node] = true;
//         totalWeight += weight;

//         // 更新邻居
//         for (const auto& [w, neighbor] : graph[node]) {
//             if (!visited[neighbor] && w < dist[neighbor]) {
//                 dist[neighbor] = w;
//                 pq.push({w, neighbor});
//             }
//         }
//     }

//     // 检查是否所有节点都访问过（连通）
//     for (int i = 1; i <= n; i++) {
//         if (!visited[i]) {
//             cout << "Graph is not connected" << endl;
//             return 0;
//         }
//     }

//     cout << totalWeight << endl;

//     return 0;
// }