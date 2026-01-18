#include <bits/stdc++.h>
using namespace std;

vector<int> parent;
struct Edge
{
    int u, v;
    long long weight;
    Edge(int a, int b, int c) : u(a), v(b), weight(c)
    {
    }
    bool operator<(const Edge& other) const
    {
        return this->weight < other.weight;
    }
};

int find(int i)
{
    if (parent[i] != i) parent[i] = find(parent[i]);
    return parent[i];
}

bool setUnion(int x, int y)
{
    int rootx = find(x);
    int rooty = find(y);
    if (rootx == rooty) return false;
    parent[rootx] = rooty;
    return true;
}

int main()
{
    int m, n;
    cin >> m >> n;
    vector<Edge> edges;
    for (int i = 0; i < n; i++)
    {
        int u, v;
        long long w;
        cin >> u >> v >> w;
        edges.push_back(Edge(u, v, w));
    }

    stable_sort(edges.begin(), edges.end());
    sort(edges.begin(), edges.end());
    parent.resize(m + 1);
    for (int i = 0; i <= m; i++)
    {
        parent[i] = i;
    }

    long long totalw = 0;
    int count = 0;
    for (const auto& edge : edges)
    {
        if (setUnion(edge.u, edge.v))
        {
            count++;
            totalw += edge.weight;
            if (count == m - 1) break;
        }
    }

    cout << totalw << endl;
}