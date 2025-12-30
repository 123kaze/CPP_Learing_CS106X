#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
// Tree.cpp
#include "Treenode.h"
#include <iostream>
#include <vector>
using namespace std;

// 声明全局变量（如果在levelOrder_BFS.cpp中使用了）
extern vector<int> res;

int main()
{
    // 构建二叉树：    1
    //              /   \
    //             2     3
    //            / \   /
    //           4   5 6
    TreeNode* root = new TreeNode(1);
    root->left = new TreeNode(2);
    root->right = new TreeNode(3);
    root->left->left = new TreeNode(4);
    root->left->right = new TreeNode(5);
    root->right->left = new TreeNode(6);
    
    vector<int> preResult, inResult, postResult;
    
    // 测试前中后序遍历
    cout << "=== Pre/In/Post Order Traversal ===" << endl;
    cout << "Pre-order:";
    preOrder(root, preResult);
    cout << endl;
    
    cout << "In-order:";
    inOrder(root, inResult);
    cout << endl;
    
    cout << "Post-order:";
    postOrder(root, postResult);
    cout << endl;
    
    // 测试层次遍历
    cout << "\n=== Level Order Traversal ===" << endl;
    levelOrder(root);
    
    // 打印全局变量结果
    cout << "\nLevel order stored in global vector: ";
    for(int num : res) cout << num << " ";
    cout << endl;
    
    return 0;
}