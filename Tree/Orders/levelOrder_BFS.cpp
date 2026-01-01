// Orders/levelOrder_BFS.cpp
#include "../Treenode.h"
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