#include <climits>
#include <iostream>
#include <queue>
#include <vector>

using namespace std;

// 定义边：目的地和权重
struct Edge
{
    int to;
    int weight;
};

// 定义优先队列中的节点：当前距离和点编号
struct Node
{
    int dist;
    int u;
    // 优先队列默认为大顶堆，我们需要重载比较运算符实现小顶堆（距离越小优先级越高）
    bool operator>(const Node& other) const
    {
        return dist > other.dist;
    }
};

void dijkstra(int start, int n, const vector<vector<Edge>>& adj)
{
    // dist 数组，初始化为无穷大
    vector<int> dist(n + 1, INT_MAX);
    // 记录路径（可选）：pre[v] 表示到达 v 的前驱节点
    vector<int> pre(n + 1, -1);

    // 小顶堆优化
    priority_queue<Node, vector<Node>, greater<Node>> pq;

    // 起点初始化
    dist[start] = 0;
    pq.push({0, start});

    while (!pq.empty())
    {
        Node top = pq.top();
        pq.pop();

        int d = top.dist;
        int u = top.u;

        // 关键：如果从堆中取出的距离已经大于当前记录的最短距离，说明是失效的老数据，跳过
        if (d > dist[u]) continue;

        // 遍历 u 的所有邻居进行松弛操作
        for (const auto& edge : adj[u])
        {
            int v = edge.to;
            int weight = edge.weight;

            // 松弛操作：如果 经过 u 到达 v 的距离更短
            if (dist[u] + weight < dist[v])
            {
                dist[v] = dist[u] + weight;
                pre[v] = u;
                pq.push({dist[v], v});
            }
        }
    }

    // 输出结果
    cout << "从起点 " << start << " 到各点的最短距离如下：" << endl;
    for (int i = 1; i <= n; ++i)
    {
        if (dist[i] == INT_MAX)
            cout << i << ": 不可达" << endl;
        else
            cout << i << ": " << dist[i] << endl;
    }
}

int main()
{
    int n = 5, m = 6;  // 5个点，6条边
    vector<vector<Edge>> adj(n + 1);

    // 构造图（起点, 终点, 权重）
    adj[1].push_back({2, 2});
    adj[1].push_back({3, 5});
    adj[2].push_back({3, 2});
    adj[2].push_back({4, 6});
    adj[3].push_back({4, 3});
    adj[4].push_back({5, 1});

    dijkstra(1, n, adj);

    return 0;
}