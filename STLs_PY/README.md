# STLs_PY - Python 标准库容器示例

本目录包含 Python 标准库中常用容器的示例代码，类似于 C++ STL 的 Python 版本。

## 文件列表

| 文件名 | 对应 C++ STL | Python 实现 | 描述 |
|--------|--------------|-------------|------|
| `list.py` | `std::vector`, `std::list` | `list` | Python 列表（动态数组） |
| `dict.py` | `std::map`, `std::unordered_map` | `dict` | Python 字典（哈希表） |
| `set.py` | `std::set`, `std::unordered_set` | `set` | Python 集合（无序不重复） |
| `tuple.py` | `std::tuple` | `tuple` | Python 元组（不可变序列） |
| `deque.py` | `std::deque` | `collections.deque` | Python 双端队列 |
| `stack.py` | `std::stack` | `list` 或 `collections.deque` | Python 栈实现 |
| `queue.py` | `std::queue` | `queue.Queue`, `collections.deque` | Python 队列实现 |
| `priority_queue.py` | `std::priority_queue` | `heapq`, `queue.PriorityQueue` | Python 优先队列 |

## 快速开始

每个文件都是独立的示例程序，可以直接运行：

```bash
cd STLs_PY
python3 list.py
python3 dict.py
python3 set.py
# ... 其他文件
```

## 详细说明

### 1. list.py - Python 列表
- **特点**：动态数组，支持随机访问
- **时间复杂度**：
  - 访问元素：O(1)
  - 插入/删除尾部：O(1)（平摊）
  - 插入/删除中间：O(n)
- **主要操作**：`append()`, `extend()`, `insert()`, `pop()`, `remove()`, 切片操作

### 2. dict.py - Python 字典
- **特点**：键值对存储，基于哈希表
- **时间复杂度**：
  - 插入/删除/查找：O(1)（平均）
  - 最坏情况：O(n)
- **主要操作**：`get()`, `setdefault()`, `update()`, `items()`, `keys()`, `values()`

### 3. set.py - Python 集合
- **特点**：无序不重复元素集
- **时间复杂度**：
  - 插入/删除/查找：O(1)（平均）
  - 集合运算：O(len(s) + len(t))
- **主要操作**：`add()`, `remove()`, `discard()`, 集合运算（并集、交集、差集）

### 4. tuple.py - Python 元组
- **特点**：不可变序列，可哈希
- **时间复杂度**：
  - 访问元素：O(1)
  - 查找元素：O(n)
- **主要操作**：元组解包，作为字典键，命名元组

### 5. deque.py - Python 双端队列
- **特点**：线程安全，两端高效操作
- **时间复杂度**：
  - 两端添加/删除：O(1)
  - 随机访问：O(n)
- **主要操作**：`appendleft()`, `popleft()`, `rotate()`, `maxlen`

### 6. stack.py - Python 栈
- **特点**：后进先出（LIFO）
- **实现方式**：使用 `list` 或 `collections.deque`
- **主要操作**：`push()`（即 `append()`）, `pop()`, `peek()`

### 7. queue.py - Python 队列
- **特点**：先进先出（FIFO），线程安全
- **实现方式**：`queue.Queue`, `collections.deque`
- **主要操作**：`put()`, `get()`, `task_done()`, `join()`

### 8. priority_queue.py - Python 优先队列
- **特点**：优先级高的元素先出队
- **实现方式**：`heapq`（最小堆）, `queue.PriorityQueue`
- **主要操作**：`heappush()`, `heappop()`, `heapify()`

## 性能比较

| 数据结构 | 主要用途 | 时间复杂度（平均） | 内存效率 |
|----------|----------|-------------------|----------|
| `list` | 动态数组，随机访问 | 访问 O(1)，插入/删除尾部 O(1) | 中等 |
| `dict` | 键值对存储，快速查找 | 插入/删除/查找 O(1) | 较低 |
| `set` | 去重，集合运算 | 插入/删除/查找 O(1) | 较低 |
| `tuple` | 不可变数据，字典键 | 访问 O(1)，创建更快 | 较高 |
| `deque` | 队列/栈，两端操作 | 两端操作 O(1) | 中等 |
| `heapq` | 优先队列 | 插入/删除 O(log n) | 较高 |

## 使用建议

1. **需要随机访问** → 使用 `list`
2. **需要键值对存储** → 使用 `dict`
3. **需要去重或集合运算** → 使用 `set`
4. **需要不可变数据或字典键** → 使用 `tuple`
5. **需要队列或栈** → 使用 `collections.deque`
6. **需要线程安全队列** → 使用 `queue.Queue`
7. **需要优先队列** → 使用 `heapq` 或 `queue.PriorityQueue`

## 与 C++ STL 的对应关系

| C++ STL | Python 等效 | 主要区别 |
|---------|-------------|----------|
| `std::vector` | `list` | Python 列表是动态数组，不是链表 |
| `std::list` | `collections.deque` | 双向链表功能，但 `deque` 不是严格链表 |
| `std::deque` | `collections.deque` | 功能相似 |
| `std::map` | `dict` | Python 字典是无序的（Python 3.6+ 保持插入顺序） |
| `std::unordered_map` | `dict` | Python 字典就是哈希表实现 |
| `std::set` | `set` | Python 集合是无序的 |
| `std::unordered_set` | `set` | Python 集合就是哈希表实现 |
| `std::stack` | `list` 或 `collections.deque` | 需要自己封装 |
| `std::queue` | `queue.Queue` 或 `collections.deque` | `queue.Queue` 是线程安全的 |
| `std::priority_queue` | `heapq` 或 `queue.PriorityQueue` | 最小堆实现 |

## 示例代码结构

每个示例文件都包含：
1. 文件头注释说明
2. `main()` 函数作为入口点
3. 分章节演示各种操作
4. 实际应用场景
5. 性能提示和注意事项

## 扩展学习

- [Python 官方文档 - 内置类型](https://docs.python.org/3/library/stdtypes.html)
- [Python 官方文档 - collections 模块](https://docs.python.org/3/library/collections.html)
- [Python 官方文档 - heapq 模块](https://docs.python.org/3/library/heapq.html)
- [Python 官方文档 - queue 模块](https://docs.python.org/3/library/queue.html)

## 贡献

这些示例代码旨在帮助理解 Python 标准库容器的使用。如果您发现任何问题或有改进建议，欢迎提交 Issue 或 Pull Request。
