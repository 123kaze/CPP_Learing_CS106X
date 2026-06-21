class Solution:
    def reverseBetween(self, head, left, right):
        dummy = ListNode(0)
        dummy.next = head

        pre = dummy

        # 找到 left 前一个节点
        for _ in range(left - 1):
            pre = pre.next

        cur = pre.next

        # 头插法反转
        for _ in range(right - left):
            nxt = cur.next

            cur.next = nxt.next
            nxt.next = pre.next
            pre.next = nxt

        return dummy.next