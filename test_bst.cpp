#include <iostream>
#include <vector>
#include <sstream>
#include "Tree/BSTree/BST.cpp"

using namespace std;

int main() {
    // 测试用例1: 题目中的样例
    {
        cout << "Test Case 1 (Sample from problem):" << endl;
        vector<int> data = {3, 1, 6, 4, 2, 6, 5, 7};
        
        if (data.empty()) {
            cout << "Empty tree" << endl;
            cout << "Expected: (empty)" << endl;
            cout << endl;
        } else {
            BSTNode* root = new BSTNode(data[0]);
            for (size_t i = 1; i < data.size(); i++) {
                root->insert(data[i]);
            }
            
            vector<int> result;
            root->preOrder(result);
            
            cout << "Input: ";
            for (int val : data) {
                cout << val << " ";
            }
            cout << endl;
            
            cout << "Output: ";
            for (int val : result) {
                cout << val << " ";
            }
            cout << endl;
            
            cout << "Expected: 3 1 0 2 0 0 6 4 0 5 0 0 7 0 0 " << endl;
            
            // 清理内存
            // 注意：这里需要实现树的删除，但为了简单起见先跳过
            cout << endl;
        }
    }
    
    // 测试用例2: 单个元素
    {
        cout << "Test Case 2 (Single element):" << endl;
        vector<int> data = {5};
        
        BSTNode* root = new BSTNode(data[0]);
        vector<int> result;
        root->preOrder(result);
        
        cout << "Input: 5" << endl;
        cout << "Output: ";
        for (int val : result) {
            cout << val << " ";
        }
        cout << endl;
        
        cout << "Expected: 5 0 0 " << endl;
        cout << endl;
    }
    
    // 测试用例3: 升序序列
    {
        cout << "Test Case 3 (Ascending sequence):" << endl;
        vector<int> data = {1, 2, 3, 4, 5};
        
        BSTNode* root = new BSTNode(data[0]);
        for (size_t i = 1; i < data.size(); i++) {
            root->insert(data[i]);
        }
        
        vector<int> result;
        root->preOrder(result);
        
        cout << "Input: 1 2 3 4 5" << endl;
        cout << "Output: ";
        for (int val : result) {
            cout << val << " ";
        }
        cout << endl;
        
        cout << "Expected: 1 0 2 0 3 0 4 0 5 0 0 " << endl;
        cout << endl;
    }
    
    // 测试用例4: 降序序列
    {
        cout << "Test Case 4 (Descending sequence):" << endl;
        vector<int> data = {5, 4, 3, 2, 1};
        
        BSTNode* root = new BSTNode(data[0]);
        for (size_t i = 1; i < data.size(); i++) {
            root->insert(data[i]);
        }
        
        vector<int> result;
        root->preOrder(result);
        
        cout << "Input: 5 4 3 2 1" << endl;
        cout << "Output: ";
        for (int val : result) {
            cout << val << " ";
        }
        cout << endl;
        
        cout << "Expected: 5 4 3 2 1 0 0 0 0 0 0 " << endl;
        cout << endl;
    }
    
    // 测试用例5: 重复元素
    {
        cout << "Test Case 5 (Duplicate elements):" << endl;
        vector<int> data = {2, 2, 2, 2, 2};
        
        BSTNode* root = new BSTNode(data[0]);
        for (size_t i = 1; i < data.size(); i++) {
            root->insert(data[i]);
        }
        
        vector<int> result;
        root->preOrder(result);
        
        cout << "Input: 2 2 2 2 2" << endl;
        cout << "Output: ";
        for (int val : result) {
            cout << val << " ";
        }
        cout << endl;
        
        cout << "Expected: 2 0 0 " << endl;
        cout << endl;
    }
    
    cout << "All test cases completed." << endl;
    
    return 0;
}
