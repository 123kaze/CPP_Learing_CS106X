struct ListNode
{
    int val;
    ListNode* next;
    ListNode() : val(0), next(nullptr)
    {
    }
    ListNode(int x) : val(x), next(nullptr)
    {
    }
    ListNode(int x, ListNode* next) : val(x), next(next)
    {
    }
};

class Solution
{
   public:
    ListNode* removeElements(ListNode* head, int val)
    {
        while (head != nullptr && head->val == val)
        {
            ListNode* temp = head;
            head = head->next;
            delete temp;  // 如果需要释放内存
        }

        if (head == nullptr)
        {
            return nullptr;
        }
        ListNode* p = head;
        while (p->next != nullptr)
        {
            if (p->next->val == val)
            {
                ListNode* q = p->next->next;
                p->next = q;
            }
            else
            {
                p = p->next;
            }
        }
        return head;
    }
};

// 也可以通过递归的办法做

// 实际上，先做递归出口nullpter,然后
// 在等于的时候，我们直接新建一个head,跳过当前head,达到删除效果
// 这个也就起到一个判断的作用
ListNode* removeElements(ListNode* head, int val)
{
    // 基础情况：空链表
    if (head == nullptr)
    {
        return nullptr;
    }

    // 递归处理
    if (head->val == val)
    {
        ListNode* newHead = removeElements(head->next, val);
        delete head;
        return newHead;
    }
    else
    {
        head->next = removeElements(head->next, val);
        return head;
    }
}
