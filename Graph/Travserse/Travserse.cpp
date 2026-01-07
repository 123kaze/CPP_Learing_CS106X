#include <iostream>
#include <queue>
#include <vector>

#include "../Treenode.h"
#include "Graph/grapgh1.h"
using namespace std;

// 图的遍历框架
// 在实际做题的时候，我们只需要一个adj矩阵，一个mark数组或者parent数组就
// 和一个queue或者stack就可以了。哦对，还有节点数量n

void doTravserse(Graph* G, int startVertex)
{
    int n = G->n();
    vector<int> parent(n, -1);          // 记录每个节点的父节点
    queue<int> q;                       // 用于BFS的队列
    parent[startVertex] = startVertex;  // 根节点的父节点设为自己
    q.push(startVertex);

    while (!q.empty())
    {
        int cur = q.front();
        q.pop();
        // 处理当前节点（根据需求调整）
        // ---下面写你的操作---

        for (int next = 0; next < n; next++)
        {
            if (parent[next] == -1 && G->isEdge(cur, next))  // 也可以不要isEdge,用adj二维矩阵
            {
                parent[next] = cur;
                q.push(next);
            }
        }

        // 可选：在这里处理当前节点
        // 例如：cout << "Visiting node: " << current << endl;
    }

    // 可选：在这里输出遍历结果或使用parent数组
    // 例如：输出每个节点的父节点信息
    // for (int i = 0; i < n; i++) {
    //     cout << "Node " << i << " parent: " << parent[i] << endl;
    // }
}
