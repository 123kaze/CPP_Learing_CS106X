// Orders/levelOrder_BFS.cpp
#include "../Treenode.h"
#include <iostream>
#include <vector>
#include <queue>
using namespace std;


struct BSTNode : public TreeNode
{
    BSTNode(int x) : TreeNode(x) {}  // 添加构造函数
    virtual ~BSTNode() {}
    void insert(int val)
    {
        if (val < this->val)
        {
            if (left == nullptr)
                left = new BSTNode(val);
            else
                static_cast<BSTNode*>(left)->insert(val);
        }
        else if (val > this->val)
        {
            if (right == nullptr)
                right = new BSTNode(val);
            else
                static_cast<BSTNode*>(right)->insert(val);
        }
    }

    void buildBST(vector<int>& data)
    {
        for(auto it : data)
        {
            insert(it);
        }
    }

    void dfs(BSTNode* node,vector<int>& vals)
        {
           if (node == nullptr) {vals.push_back(0); return;}
           
           vals.push_back(node->val);
           dfs(static_cast<BSTNode*>(node->left),vals);
           dfs(static_cast<BSTNode*>(node->right),vals);
        }
    void preOrder(vector<int>& vals)
    {
        dfs(this,vals);
    }
};
