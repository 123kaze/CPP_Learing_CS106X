// Orders/levelOrder_BFS.cpp
#include "../Treenode.h"
#include "Graph/grapgh1.h"
#include <iostream>
#include <vector>
#include <queue>
using namespace std;

// as a Tree ,DFS is preOrder,so I get it
void preOrder(TreeNode *root,vector<int>& nums)
{
    if(root == nullptr) return;
    printf("%d/n",root->val);
    nums.push_back(root->val);
    preOrder(root->left,nums);
    preOrder(root->right,nums);
}

// 在图中，则必须有一个 "visited" 数组进行标记，也就是之前我的图中的 "setMark" 函数，不然如果有环
// 那么就会有死循环。

//我们用邻接矩阵来作图
vector<int> adj[100];
bool visited[100] {0};

void dfsGraph(int u)
{
    visited[u] = true;
    cout << "visited:" << u<<endl;
    
    //便利
    for(auto v:adj[u])
    {
        if(!visited[v]) dfsGraph(v);// 如果周围没被访问，那就继续访问。
    }
}

// PreVisit function - called before processing a vertex
void PreVisit(Graph* G, int v) {
    cout << "Entering vertex " << v << endl;
}

// PostVisit function - called after processing a vertex (backtracking)
void PostVisit(Graph* G, int v) {
    cout << "Leaving vertex " << v << " (backtracking)" << endl;
}

void DFS(Graph *G,int v)
{
    PreVisit(G,v);
    G->setMark(v,1);
    for(int w=G->first(v);w<G->n();w=G->next(v,w))
    {
        if(G->getMark(w) == 0)
            DFS(G,w);
    }
    PostVisit(G,v);
}


void graphTraverse(Graph *G){
    int v;
    for (v=0;v<G->n();v++)G->setMark(v,0);
    for (v=0;v<G->n();v++) if (G->getMark(v) == 0) DFS(G,v);
}
