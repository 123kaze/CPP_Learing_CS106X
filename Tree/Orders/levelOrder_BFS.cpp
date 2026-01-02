// Orders/levelOrder_BFS.cpp
#include "../Treenode.h"
#include "Graph/grapgh1.h"
#include <iostream>
#include <vector>
#include <queue>
using namespace std;

vector<int> res;  // 全局变量存储结果

void levelOrder(TreeNode *root)
{
    if(root == nullptr) return;
    queue<TreeNode*> q;
    q.push(root);
    
    while(!q.empty())
    {
        int size = q.size();
        for(int i = 0; i < size; i++)
        {
            TreeNode* cur = q.front();
            q.pop();
            // 这里写你需要做的过程操作
            printf(" %d", cur->val);
            res.push_back(cur->val);
            //-----------------------
            if(cur->left != nullptr) q.push(cur->left);
            if(cur->right != nullptr) q.push(cur->right);
        }
        printf("\n");
    }
}


void BFS(TreeNode *node)
{
    if(node == nullptr) return;
    queue<TreeNode*> q;
    q.push(node);

    while (!q.empty())
    {
        /* code */
        TreeNode* cur = q.front();
        q.pop();
        // -------------
        printf(" %d",cur->val);
        //--------------
        q.push(cur->left);
        q.push(cur->right);
    }
    printf("/n");
    
}

// BFS for Graph class using mark function
void BFS(Graph* G, int start)
{
    if (G == nullptr) return;
    
    // Clear all marks (0 = unvisited, 1 = visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    queue<int> q;
    
    // Mark start vertex as visited and enqueue it
    G->setMark(start, 1);
    q.push(start);
    
    cout << "BFS starting from vertex " << start << ": ";
    
    while (!q.empty()) {
        int v = q.front();
        q.pop();
        
        // Process vertex v
        cout << v << " ";
        
        // Visit all neighbors of v
        for (int w = G->first(v); w < G->n(); w = G->next(v, w)) {
            if (G->getMark(w) == 0) {  // Not visited
                G->setMark(w, 1);      // Mark as visited
                q.push(w);             // Enqueue
            }
        }
    }
    
    cout << endl;
}

// BFS for entire graph (handles disconnected graphs)
void BFS_complete(Graph* G)
{
    if (G == nullptr) return;
    
    // Clear all marks (0 = unvisited, 1 = visited)
    for (int i = 0; i < G->n(); i++) {
        G->setMark(i, 0);
    }
    
    cout << "BFS traversal of entire graph: ";
    
    // Visit all vertices
    for (int v = 0; v < G->n(); v++) {
        if (G->getMark(v) == 0) {  // Not visited
            // Start BFS from this vertex
            queue<int> q;
            G->setMark(v, 1);
            q.push(v);
            
            while (!q.empty()) {
                int current = q.front();
                q.pop();
                
                // Process vertex
                cout << current << " ";
                
                // Visit all neighbors
                for (int w = G->first(current); w < G->n(); w = G->next(current, w)) {
                    if (G->getMark(w) == 0) {
                        G->setMark(w, 1);
                        q.push(w);
                    }
                }
            }
        }
    }
    
    cout << endl;
}
