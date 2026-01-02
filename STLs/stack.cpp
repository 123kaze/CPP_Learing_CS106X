/**
 * @file stack.cpp
 * @brief stack容器用法示例
 * 
 * stack是C++标准模板库(STL)中的栈容器适配器
 * 特点：
 * 1. 后进先出(LIFO)：最后插入的元素最先被删除
 * 2. 容器适配器：基于其他容器实现（默认deque）
 * 3. 限制访问：只能访问栈顶元素
 * 4. 简单高效：操作简单，性能高效
 * 
 * 常用操作时间复杂度：
 * - 入栈(push)：O(1)
 * - 出栈(pop)：O(1)
 * - 访问栈顶(top)：O(1)
 * - 判断空(empty)：O(1)
 * - 获取大小(size)：O(1)
 */

#include <iostream>
#include <stack>
#include <vector>
#include <deque>
#include <list>

using namespace std;

int main() {
    cout << "========== stack容器用法示例 ==========" << endl;
    
    // 1. 创建stack
    cout << "\n1. 创建stack:" << endl;
    
    // 默认使用deque作为底层容器
    stack<int> stk1;
    cout << "空stack大小: " << stk1.size() << endl;
    
    // 使用vector作为底层容器
    stack<int, vector<int>> stk2;
    cout << "使用vector的stack大小: " << stk2.size() << endl;
    
    // 使用list作为底层容器
    stack<int, list<int>> stk3;
    cout << "使用list的stack大小: " << stk3.size() << endl;
    
    // 2. 基本操作
    cout << "\n2. 基本操作:" << endl;
    
    // 入栈操作
    stk1.push(10);
    stk1.push(20);
    stk1.push(30);
    stk1.push(40);
    stk1.push(50);
    
    cout << "入栈5个元素后stack大小: " << stk1.size() << endl;
    cout << "栈顶元素: " << stk1.top() << endl;
    
    // 出栈操作
    stk1.pop();
    cout << "出栈后栈顶元素: " << stk1.top() << endl;
    cout << "出栈后stack大小: " << stk1.size() << endl;
    
    // 3. 遍历stack（注意：stack不支持直接遍历）
    cout << "\n3. 遍历stack:" << endl;
    cout << "stack不支持直接遍历，需要借助临时stack" << endl;
    
    stack<int> temp_stk = stk1;
    cout << "stack元素（从栈顶到栈底）: ";
    while (!temp_stk.empty()) {
        cout << temp_stk.top() << " ";
        temp_stk.pop();
    }
    cout << endl;
    
    // 4. 判断空和获取大小
    cout << "\n4. 判断空和获取大小:" << endl;
    
    cout << "stk1是否为空: " << (stk1.empty() ? "是" : "否") << endl;
    cout << "stk1大小: " << stk1.size() << endl;
    
    // 清空stack
    while (!stk1.empty()) {
        stk1.pop();
    }
    cout << "清空后stk1是否为空: " << (stk1.empty() ? "是" : "否") << endl;
    
    // 5. 实际应用场景
    cout << "\n5. 实际应用场景:" << endl;
    
    // 场景1：括号匹配
    cout << "场景1: 括号匹配" << endl;
    string expression = "((a+b)*(c-d))";
    stack<char> paren_stack;
    bool valid = true;
    
    for (char ch : expression) {
        if (ch == '(') {
            paren_stack.push(ch);
        } else if (ch == ')') {
            if (paren_stack.empty()) {
                valid = false;
                break;
            }
            paren_stack.pop();
        }
    }
    
    if (valid && paren_stack.empty()) {
        cout << "表达式 \"" << expression << "\" 括号匹配正确" << endl;
    } else {
        cout << "表达式 \"" << expression << "\" 括号匹配错误" << endl;
    }
    
    // 场景2：逆波兰表达式求值
    cout << "\n场景2: 逆波兰表达式求值" << endl;
    vector<string> tokens = {"2", "1", "+", "3", "*"};
    stack<int> calc_stack;
    
    cout << "逆波兰表达式: ";
    for (const string& token : tokens) {
        cout << token << " ";
    }
    cout << endl;
    
    for (const string& token : tokens) {
        if (token == "+" || token == "-" || token == "*" || token == "/") {
            int b = calc_stack.top(); calc_stack.pop();
            int a = calc_stack.top(); calc_stack.pop();
            
            if (token == "+") calc_stack.push(a + b);
            else if (token == "-") calc_stack.push(a - b);
            else if (token == "*") calc_stack.push(a * b);
            else if (token == "/") calc_stack.push(a / b);
        } else {
            calc_stack.push(stoi(token));
        }
    }
    
    cout << "计算结果: " << calc_stack.top() << endl;
    
    // 场景3：函数调用栈模拟
    cout << "\n场景3: 函数调用栈模拟" << endl;
    stack<string> call_stack;
    
    call_stack.push("main()");
    cout << "调用main()，调用栈: ";
    stack<string> temp = call_stack;
    while (!temp.empty()) {
        cout << temp.top() << " ";
        temp.pop();
    }
    cout << endl;
    
    call_stack.push("func1()");
    cout << "调用func1()，调用栈: ";
    temp = call_stack;
    while (!temp.empty()) {
        cout << temp.top() << " ";
        temp.pop();
    }
    cout << endl;
    
    call_stack.push("func2()");
    cout << "调用func2()，调用栈: ";
    temp = call_stack;
    while (!temp.empty()) {
        cout << temp.top() << " ";
        temp.pop();
    }
    cout << endl;
    
    call_stack.pop();
    cout << "func2()返回，调用栈: ";
    temp = call_stack;
    while (!temp.empty()) {
        cout << temp.top() << " ";
        temp.pop();
    }
    cout << endl;
    
    // 6. 不同底层容器的性能比较
    cout << "\n6. 不同底层容器的性能比较:" << endl;
    
    cout << "1. 默认使用deque: 综合性能最好，内存使用适中" << endl;
    cout << "2. 使用vector: 内存连续，缓存友好，但扩容时需要复制所有元素" << endl;
    cout << "3. 使用list: 每个操作都是O(1)，但内存开销大，缓存不友好" << endl;
    cout << "4. 选择建议: 大多数情况下使用默认deque即可" << endl;
    
    // 7. 自定义stack示例
    cout << "\n7. 自定义stack示例:" << endl;
    
    // 使用自定义比较函数的stack
    stack<int> custom_stk;
    
    // 模拟最小栈
    stack<int> main_stack;
    stack<int> min_stack;
    
    // 入栈操作
    auto push_min_stack = [&](int val) {
        main_stack.push(val);
        if (min_stack.empty() || val <= min_stack.top()) {
            min_stack.push(val);
        }
    };
    
    // 出栈操作
    auto pop_min_stack = [&]() {
        if (main_stack.top() == min_stack.top()) {
            min_stack.pop();
        }
        main_stack.pop();
    };
    
    // 获取最小值
    auto get_min = [&]() {
        return min_stack.top();
    };
    
    push_min_stack(5);
    push_min_stack(3);
    push_min_stack(7);
    push_min_stack(2);
    push_min_stack(8);
    
    cout << "当前栈: ";
    stack<int> temp_main = main_stack;
    while (!temp_main.empty()) {
        cout << temp_main.top() << " ";
        temp_main.pop();
    }
    cout << endl;
    cout << "当前最小值: " << get_min() << endl;
    
    pop_min_stack();
    cout << "出栈后最小值: " << get_min() << endl;
    
    // 8. 性能提示
    cout << "\n8. 性能提示:" << endl;
    cout << "1. stack是容器适配器，不是容器，它基于其他容器实现" << endl;
    cout << "2. 如果需要频繁访问中间元素，不要使用stack" << endl;
    cout << "3. stack的pop()不返回元素，需要先top()再pop()" << endl;
    cout << "4. 注意stack的empty()判断，避免在空栈上调用top()或pop()" << endl;
    cout << "5. 根据应用场景选择合适的底层容器" << endl;
    
    cout << "\n========== stack示例结束 ==========" << endl;
    
    return 0;
}
