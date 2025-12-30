// Tree.cpp
#include <iostream>
#include <vector>
#include <queue>
#include <chrono>  // 添加时间库
#include <random>  // 用于生成随机树
#include <iomanip> // 用于格式化输出
#include "Treenode.h"

using namespace std;
using namespace std::chrono;  // 简化chrono命名空间

extern vector<int> res;  // 声明外部全局变量

TreeNode* createTree(int depth, int& value) {
    if (depth <= 0) return nullptr;
    
    TreeNode* root = new TreeNode(value++);
    root->left = createTree(depth - 1, value);
    root->right = createTree(depth - 1, value);
    return root;
}

// 清理二叉树内存
void deleteTree(TreeNode* root) {
    if (root == nullptr) return;
    deleteTree(root->left);
    deleteTree(root->right);
    delete root;
}

// 主函数
int main()
{
    cout << "=== 二叉树遍历性能测试 ===" << endl;
    
    // 创建不同规模的树进行测试
    vector<int> treeDepths = {10, 15, 18};  // 树的深度
    vector<int> results;  // 存储遍历结果
    
    for (int depth : treeDepths) {
        cout << "\n测试树深度: " << depth << endl;
        cout << "节点数约: " << (1 << depth) - 1 << endl;  // 2^depth - 1
        cout << "--------------------------------" << endl;
        
        int startValue = 1;
        TreeNode* root = createTree(depth, startValue);
        
        // 1. 测试前序遍历
        results.clear();
        auto start = high_resolution_clock::now();
        preOrder(root, results);
        auto end = high_resolution_clock::now();
        auto duration = duration_cast<microseconds>(end - start);
        cout << "前序遍历时间: " << setw(8) << duration.count() << " μs (" 
             << fixed << setprecision(2) << duration.count() / 1000.0 << " ms)" << endl;
        
        // 2. 测试中序遍历
        results.clear();
        start = high_resolution_clock::now();
        inOrder(root, results);
        end = high_resolution_clock::now();
        duration = duration_cast<microseconds>(end - start);
        cout << "中序遍历时间: " << setw(8) << duration.count() << " μs (" 
             << fixed << setprecision(2) << duration.count() / 1000.0 << " ms)" << endl;
        
        // 3. 测试后序遍历
        results.clear();
        start = high_resolution_clock::now();
        postOrder(root, results);
        end = high_resolution_clock::now();
        duration = duration_cast<microseconds>(end - start);
        cout << "后序遍历时间: " << setw(8) << duration.count() << " μs (" 
             << fixed << setprecision(2) << duration.count() / 1000.0 << " ms)" << endl;
        
        // 4. 测试层次遍历
        res.clear();
        start = high_resolution_clock::now();
        levelOrder(root);
        end = high_resolution_clock::now();
        duration = duration_cast<microseconds>(end - start);
        cout << "层次遍历时间: " << setw(8) << duration.count() << " μs (" 
             << fixed << setprecision(2) << duration.count() / 1000.0 << " ms)" << endl;
        
        // 清理内存
        deleteTree(root);
    }
    
    // 额外：单个函数的详细测试
    cout << "\n=== 详细性能对比 ===" << endl;
    {
        int depth = 15;
        int startValue = 1;
        TreeNode* root = createTree(depth, startValue);
        results.clear();
        
        // 多次运行取平均值
        int runs = 10;
        long long totalTime = 0;
        
        for (int i = 0; i < runs; i++) {
            results.clear();
            auto start = high_resolution_clock::now();
            preOrder(root, results);
            auto end = high_resolution_clock::now();
            totalTime += duration_cast<microseconds>(end - start).count();
        }
        
        cout << "\n前序遍历 " << runs << " 次平均时间: " 
             << totalTime / runs << " μs" << endl;
        cout << "遍历节点数: " << results.size() << endl;
        
        deleteTree(root);
    }
    
    return 0;
}
