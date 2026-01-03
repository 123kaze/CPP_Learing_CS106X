// TreeNode.h
#ifndef TREENODE_H
#define TREENODE_H

#include <vector>
using namespace std;

struct TreeNode
{
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x):val(x),left(nullptr),right(nullptr) {}

    bool operator<(const TreeNode *Other)
    {
        return this->val < Other->val;
    }
};

// 前中后序遍历声明
void preOrder(TreeNode* root, vector<int>& a);
void inOrder(TreeNode* root, vector<int>& a);
void postOrder(TreeNode* root, vector<int>& a);

// 层次遍历声明
void levelOrder(TreeNode* root);

#endif