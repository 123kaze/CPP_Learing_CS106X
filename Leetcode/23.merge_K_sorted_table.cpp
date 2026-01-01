#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <queue>
using namespace std;

struct ListNode {
    int val;
    ListNode *next;
    ListNode() : val(0), next(nullptr) {}
    ListNode(int x) : val(x), next(nullptr) {}
    ListNode(int x, ListNode *next) : val(x), next(next) {}
    bool operator<(const ListNode& other) const {
        return val < other.val;  // 最大堆
    }
};

// struct ListNode {
//     int val;
//     ListNode* next;
//     ListNode(int x) : val(x), next(nullptr) {}
    
//     // 重载<运算符，用于默认最大堆
//     bool operator<(const ListNode& other) const {
//         return val < other.val;  // 最大堆
//     }
// };

struct ListNodeComparator {
    bool operator()(ListNode* a, ListNode* b) {
        return a->val > b->val;  // 最小堆：小的在前
    }
};

ListNode*  mergeKlist(vector<ListNode*>& lists)
{
    ListNode* fakeHead = new ListNode(0);
    ListNode* p = fakeHead;
    int k = lists.size();
    // priority_queue<ListNode> heap = 
    priority_queue<ListNode*, vector<ListNode*>, ListNodeComparator> heap;
    for (int i=0;i<k;i++)
    {
        if(lists[i] != nullptr)
        {
            heap.push(lists[i]);
        }
    }

    while(!heap.empty())
    {
        ListNode* node = heap.top();
        heap.pop();
        p->next = node;
        p = p->next;

        if(node->next != nullptr)
        { 
            heap.push(node->next);
        }
    }
    return fakeHead->next;
}