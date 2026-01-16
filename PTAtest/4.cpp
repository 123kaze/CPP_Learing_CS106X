#include <bits/stdc++.h>

using namespace std;

int idx = 0;
class TreeNode
{
   public:
    char val;
    int deep;
    TreeNode* left;
    TreeNode* right;
    TreeNode(char x) : val(x), left(nullptr), right(nullptr)
    {
    }
    bool operator<(const TreeNode* Other)
    {
        return this->val < Other->val;
    }
};

TreeNode* buildTree(string& pre)
{
    if (idx >= pre.length() || pre[idx] == '*')
    {
        idx++;
        return nullptr;
    }
    TreeNode* root = new TreeNode(pre[idx]);

    root->left = buildTree(pre);
    root->right = buildTree(pre);
    return root;
}

int depth(TreeNode* root)
{
    if (root == nullptr)
    {
        return 0;
    }
    int leftd = depth(root->left);
    int rigd = depth(root->right);
    return max(leftd, rigd) + 1;
}

int main()
{
    string pre;
    TreeNode* root;
    int res = 0;
    while (cin >> pre)
    {
        idx = 0;
        root = buildTree(pre);
        res = depth(root);
        printf("%d\n", res);
    }
}
