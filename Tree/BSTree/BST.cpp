// Orders/levelOrder_BFS.cpp
#include "../Treenode.h"
#include <iostream>
#include <vector>
#include <queue>
using namespace std;

class BSTNode : public TreeNode
{
public:
    // 构造函数
    BSTNode(int x) : TreeNode(x) {}
    
    // 虚析构函数
    virtual ~BSTNode() {
        // 如果需要清理资源，可以在这里添加
    }
    
    // 插入节点
    void insert(int val) {
        if (val < this->val) {
            if (left == nullptr) {
                left = new BSTNode(val);
            } else {
                // 安全转换：假设所有节点都是BSTNode
                BSTNode* leftNode = dynamic_cast<BSTNode*>(left);
                if (leftNode) {
                    leftNode->insert(val);
                } else {
                    // 如果不是BSTNode，创建新节点（这种情况不应该发生）
                    delete left;
                    left = new BSTNode(val);
                }
            }
        } else if (val > this->val) {
            if (right == nullptr) {
                right = new BSTNode(val);
            } else {
                BSTNode* rightNode = dynamic_cast<BSTNode*>(right);
                if (rightNode) {
                    rightNode->insert(val);
                } else {
                    delete right;
                    right = new BSTNode(val);
                }
            }
        }
        // 如果val == this->val，不插入重复值
    }
    
    // 构建BST
    void buildBST(const vector<int>& data) {
        for (int val : data) {
            insert(val);
        }
    }
    
    // DFS辅助函数
    void dfs(TreeNode* node, vector<int>& vals) {
        if (node == nullptr) {
            vals.push_back(0); 
            return;
        }
        vals.push_back(node->val);
        dfs(node->left, vals);
        dfs(node->right, vals);
    }
    
    // 前序遍历
    void preOrder(vector<int>& vals) {
        vals.clear();
        dfs(this, vals);
    }
    
    // 层序遍历（BFS）
    vector<vector<int>> levelOrder() {
        vector<vector<int>> result;
        if (this == nullptr) return result;
        
        queue<TreeNode*> q;
        q.push(this);
        
        while (!q.empty()) {
            int levelSize = q.size();
            vector<int> currentLevel;
            
            for (int i = 0; i < levelSize; ++i) {
                TreeNode* node = q.front();
                q.pop();
                
                if (node) {
                    currentLevel.push_back(node->val);
                    
                    // 添加子节点到队列
                    if (node->left) q.push(node->left);
                    if (node->right) q.push(node->right);
                } else {
                    currentLevel.push_back(0);
                }
            }
            result.push_back(currentLevel);
        }
        
        return result;
    }
    
    // 查找节点
    static BSTNode* search(BSTNode* root, int key) {
        BSTNode* current = root;
        while (current != nullptr) {
            if (key == current->val) {
                return current;
            } else if (key < current->val) {
                // 使用动态转换，更安全
                current = dynamic_cast<BSTNode*>(current->left);
            } else {
                current = dynamic_cast<BSTNode*>(current->right);
            }
        }
        return nullptr;
    }
    
    // 更安全的查找（带类型检查）
    static BSTNode* searchSafe(TreeNode* root, int key) {
        TreeNode* current = root;
        while (current != nullptr) {
            if (key == current->val) {
                return dynamic_cast<BSTNode*>(current);
            } else if (key < current->val) {
                current = current->left;
            } else {
                current = current->right;
            }
        }
        return nullptr;
    }
    
    // 获取最小值节点
    BSTNode* getMinNode() {
        BSTNode* current = this;
        while (current && current->left) {
            current = dynamic_cast<BSTNode*>(current->left);
        }
        return current;
    }
    
    // 获取最大值节点
    BSTNode* getMaxNode() {
        BSTNode* current = this;
        while (current && current->right) {
            current = dynamic_cast<BSTNode*>(current->right);
        }
        return current;
    }
    
    // 中序遍历（有序输出）
    void inOrder(vector<int>& vals) {
        vals.clear();
        inOrderTraversal(this, vals);
    }
    
private:
    // 私有辅助函数
    void inOrderTraversal(TreeNode* node, vector<int>& vals) {
        if (node == nullptr) return;
        
        inOrderTraversal(node->left, vals);
        vals.push_back(node->val);
        inOrderTraversal(node->right, vals);
    }
};