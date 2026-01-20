#include <bits/stdc++.h>

#include <vector>

using namespace std;

struct TreeNode
{
    int val;
    TreeNode* left;
    TreeNode* right;
    TreeNode(int x) : val(x), left(nullptr), right(nullptr)
    {
    }
};

class Solution
{
   public:
    TreeNode* buildTree(vector<int>& inorder, vector<int>& postorder)
    {
        return build(inorder, 0, inorder.size() - 1, postorder, 0, postorder.size() - 1);
    }

   private:
    TreeNode* build(vector<int>& inorder, int inStart, int inEnd, vector<int>& postorder,
                    int postStart, int postEnd)
    {
        // base case: 区间无效
        if (inStart > inEnd || postStart > postEnd)
        {
            return nullptr;
        }

        // 1. 后序遍历的最后一个元素是根节点
        int rootVal = postorder[postEnd];
        TreeNode* root = new TreeNode(rootVal);

        // 2. 在中序遍历中找到根节点的位置
        int rootIndex;
        for (rootIndex = inStart; rootIndex <= inEnd; rootIndex++)
        {
            if (inorder[rootIndex] == rootVal)
            {
                break;
            }
        }

        // 3. 计算左子树的大小
        int leftSize = rootIndex - inStart;

        // 4. 递归构建左右子树
        // 左子树：
        //   - 中序遍历：inStart 到 rootIndex-1
        //   - 后序遍历：postStart 到 postStart+leftSize-1
        root->left =
            build(inorder, inStart, rootIndex - 1, postorder, postStart, postStart + leftSize - 1);

        // 右子树：
        //   - 中序遍历：rootIndex+1 到 inEnd
        //   - 后序遍历：postStart+leftSize 到 postEnd-1
        root->right =
            build(inorder, rootIndex + 1, inEnd, postorder, postStart + leftSize, postEnd - 1);

        return root;
    }
};

TreeNode* buildTree(vector<int>& inorder, vector<int>& postorder)
{
    return build(inorder, 0, inorder.size() - 1, postorder, 0, postorder.size() - 1);
};

TreeNode* build(vector<int>& inorder, int inStart, int inEnd, vector<int>& postorder, int postStart,
                int postEnd)
{
    if (inStart > inEnd || postStart > postEnd)
    {
        return nullptr;
    }

    int root1 = postorder[postEnd];

    int idx = 0;
    for (int i = inStart; i < inEnd;
         i++)  // 这里可以等于，因为你之前已经-1了   // i 的初始是 inStart!!!
    {
        if (inorder[i] == root1)
        {
            idx = i;
            break;
        }
    }

    TreeNode* root = new TreeNode(root1);
    int leftsize = idx - inStart;
    root->left = build(inorder, inStart, idx - 1, postorder, postStart, postStart + leftsize - 1);
    root->right = build(inorder, idx + 1, inEnd, postorder, postStart + leftsize, postEnd - 1);

    return root;
}