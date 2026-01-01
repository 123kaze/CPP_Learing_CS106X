// Orders/pre_in_postOrders.cpp
#include "../Treenode.h"
#include <iostream>
#include <vector>
using namespace std;

void preOrder(TreeNode* root, vector<int>& a)
{
    if(root == nullptr) return;
    //也可以替换成你要的操作
    printf(" %d",root->val);
    a.push_back(root->val);
    preOrder(root->left,a);
    preOrder(root->right,a);
}

void inOrder(TreeNode* root, vector<int>& a)
{
    if(root == nullptr) return;
    inOrder(root->left,a);
    printf(" %d",root->val);
    a.push_back(root->val);
    inOrder(root->right,a);
}

void postOrder(TreeNode* root, vector<int>& a)
{
    if(root == nullptr) return;
    postOrder(root->left,a);
    postOrder(root->right,a);
    printf(" %d",root->val);
    a.push_back(root->val);
}