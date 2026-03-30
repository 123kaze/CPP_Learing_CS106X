import heapq
from collections import defaultdict

class EventManager:
    def __init__(self, events: list[list[int]]):
        self.events = {eventId: priority for eventId, priority in events}
        # 最大堆：存储 (-priority, eventId)
        self.heap = [(-priority, eventId) for eventId, priority in events]
        heapq.heapify(self.heap)
        # 记录待删除的事件（用于延迟删除）
        self.to_remove = set()

    def updatePriority(self, eventId: int, newPriority: int) -> None:
        # 标记旧事件为待删除
        self.to_remove.add(eventId)
        # 更新字典
        self.events[eventId] = newPriority
        # 添加新事件到堆
        heapq.heappush(self.heap, (-newPriority, eventId))

    def pollHighest(self) -> int:
        # 清理堆顶的无效事件
        while self.heap:
            neg_priority, eventId = self.heap[0]
            if eventId in self.to_remove:
                heapq.heappop(self.heap)
                self.to_remove.remove(eventId)
            elif eventId not in self.events:
                heapq.heappop(self.heap)
            else:
                break

        if not self.heap:
            return -1

        # 弹出最高优先级事件
        neg_priority, eventId = heapq.heappop(self.heap)

        # 处理相同优先级的情况：选择最小ID
        # 收集所有相同优先级的候选
        candidates = [eventId]
        priority = -neg_priority

        # 检查堆顶是否还有相同优先级的
        while self.heap and -self.heap[0][0] == priority:
            _, next_id = heapq.heappop(self.heap)
            if next_id in self.events and self.events[next_id] == priority:
                candidates.append(next_id)
            else:
                # 如果是无效事件，跳过
                continue

        # 选择最小ID
        result = min(candidates)

        # 将其他相同优先级的放回堆中
        for candidate in candidates:
            if candidate != result:
                heapq.heappush(self.heap, (-priority, candidate))

        # 删除事件
        del self.events[result]
        return result