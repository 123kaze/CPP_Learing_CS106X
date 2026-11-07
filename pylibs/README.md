# pylibs - Python 算法题常用标准库示例

仿照 `../STLs/` 的介绍方式：文件头说明用途和复杂度，`main()` 按编号演示常用操作，最后给出算法应用和易错点。所有示例只使用 Python 标准库，不需要安装第三方包，兼容 Python 3.8 及以上版本。

## 文件列表与选型

| 文件 | 标准库 | 算法题中的用途 | 优先记住的 API |
|------|--------|----------------|----------------|
| [datetime_example.py](datetime_example.py) | `datetime`、`calendar` | 日期差、日期偏移、星期、年内第几天、闰年 | `date`、`timedelta`、`strptime`、`weekday` |
| [collections_example.py](collections_example.py) | `collections` | BFS、频次统计、分组、滑动窗口最大值 | `deque`、`Counter`、`defaultdict` |
| [heapq_example.py](heapq_example.py) | `heapq` | 优先队列、Top K、合并代价、Dijkstra | `heapify`、`heappush`、`heappop` |
| [bisect_example.py](bisect_example.py) | `bisect` | 有序数组查找、区间计数、最长递增子序列 | `bisect_left`、`bisect_right`、`insort` |
| [math_example.py](math_example.py) | `math` | 最大公约数、整数开方、组合数、排列数 | `gcd`、`isqrt`、`comb`、`perm` |
| [itertools_example.py](itertools_example.py) | `itertools` | 排列组合枚举、笛卡尔积、前缀和、分组 | `permutations`、`combinations`、`product`、`accumulate` |
| [functools_example.py](functools_example.py) | `functools` | 记忆化搜索、自定义排序规则 | `lru_cache`、`cmp_to_key` |
| [test_all.py](test_all.py) | `unittest` | 验证示例算法和边界条件 | `python3 -B test_all.py` |

文件名故意使用 `_example.py` 后缀。不要命名为 `datetime.py`、`math.py`、`collections.py` 等，否则当前目录下的文件可能遮蔽同名标准库，导致导入失败。

## 快速开始

在项目根目录运行：

```bash
python3 pylibs/datetime_example.py
python3 pylibs/collections_example.py
python3 pylibs/heapq_example.py
python3 pylibs/bisect_example.py
python3 pylibs/math_example.py
python3 pylibs/itertools_example.py
python3 pylibs/functools_example.py
python3 -B pylibs/test_all.py
```

每个示例都可以独立运行，不需要输入；输出使用固定数据，便于对照代码。导入示例文件不会自动打印。提交到 OJ 时只取需要的标准库导入和算法代码，不要提交演示用的 `main()` 或多余的说明输出。

## datetime：做日期题先看这里

只处理年月日时用 `date`；题目还有时分秒时用 `datetime`；表示相隔多少天、多少秒时用 `timedelta`。

| 需求 | 写法 | 说明 |
|------|------|------|
| 创建日期 | `date(2024, 2, 29)` | 无效日期会抛出 `ValueError` |
| 解析 `YYYY-MM-DD` | `date.fromisoformat(s)` | 如 `2024-02-29` |
| 解析 `YYYYMMDD` | `datetime.strptime(s, "%Y%m%d").date()` | 如 `20240229` |
| 输出年月日 | `d.isoformat()` | 输出 `YYYY-MM-DD` |
| 按格式输出 | `d.strftime("%Y/%m/%d")` | 月、日补零 |
| 两个日期相差天数 | `(end - start).days` | 有正负，不包含两端各算一天的额外计数 |
| 往后 / 往前 k 天 | `d + timedelta(days=k)` | `k` 可以为负，自动处理跨月、跨年、闰年 |
| 星期几 | `d.weekday()` | 周一为 0，周日为 6 |
| 星期几（1 到 7） | `d.isoweekday()` | 周一为 1，周日为 7 |
| 年内第几天 | `(d - date(d.year, 1, 1)).days + 1` | 1 月 1 日为第 1 天 |
| 日期转整数 | `d.toordinal()` | 公元 1 年 1 月 1 日为 1 |
| 整数转日期 | `date.fromordinal(x)` | 可用于日期离散化和还原 |
| 是否闰年 | `calendar.isleap(year)` | 1900 不是闰年，2000 是闰年 |
| 月份天数 | `calendar.monthrange(year, month)[1]` | 返回值为 `(月初星期, 当月天数)` |
| 时间差的总秒数 | `delta.total_seconds()` | 不要把 `delta.seconds` 当作总秒数 |

### 模板 1：两日期相差多少天

输入一行，包含两个 `YYYY-MM-DD` 日期，输出它们相隔的天数，不计方向。

```python
from datetime import date

start, end = map(date.fromisoformat, input().split())
print(abs((end - start).days))
```

例如输入 `2024-02-28 2024-03-01`，输出 `2`。若题目要求起止日期都计入天数，则是 `abs((end - start).days) + 1`，本例为 `3`。

### 模板 2：某日期 k 天后的日期

输入一行，包含一个 `YYYY-MM-DD` 日期和一个整数 `k`。

```python
from datetime import date, timedelta

s, k = input().split()
answer = date.fromisoformat(s) + timedelta(days=int(k))
print(answer.isoformat())
```

例如输入 `2024-02-28 2`，输出 `2024-03-01`。

### 常见易错点

1. `timedelta` 不支持 `months` 或 `years`，一个月不一定是 30 天；`.replace()` 替换日期字段也不会自动修正非法日期。
2. `timedelta(days=2, seconds=3).seconds` 是 `3`，总秒数应取 `.total_seconds()`；负时间差也会被规范化成负天数和非负秒数。
3. `datetime.time` 是“时刻”，不是标准库 `time` 模块；两个 `time` 对象不能直接相减，需要结合日期变成 `datetime`。
4. `date` 的年份范围是 `1..9999`。题目允许公元前、超大年份或非公历规则时，需要自己实现日期计算。
5. 日期题优先使用整数天数运算，不要依赖本地时区的时间戳。`date` 与 `datetime` 混用前应先统一类型。
6. `%m` 是月份，`%M` 是分钟，`%H` 是 24 小时制小时；英文月份和星期名称受系统语言环境影响。

## 复杂度与刷题提示

| 操作 / 算法 | 时间复杂度 | 提示 |
|-------------|------------|------|
| 日期加减、比较、星期、序数转换 | `O(1)` | 在库支持的日期范围内，无需逐天模拟 |
| 固定格式日期解析 / 格式化 | 固定长度时 `O(1)` | 大量输入只含年月日时也可直接拆分成整数 |
| `deque.append` / `popleft` | `O(1)` | BFS 不要用 `list.pop(0)` |
| `Counter` 统计 n 个元素 | 平均 `O(n)` | 底层依赖哈希表 |
| 堆建堆 / 入堆 / 出堆 | `O(n)` / `O(log n)` / `O(log n)` | 堆数组整体不保证有序 |
| 二分查找 / 有序插入 | `O(log n)` / `O(n)` | `insort` 查找快，列表移动仍是线性时间 |
| 最长严格递增子序列长度 | `O(n log n)` | 示例用 `bisect_left`，重复值不延长序列 |
| `gcd(a, b)` | `O(log(min(a, b)))` 次取模 | 大整数还需考虑单次运算成本 |
| 枚举全排列 / k 元组合 | `O(n! * n)` / `O(C(n,k) * k)` | 迭代器省存储，但不能避免枚举量爆炸 |
| 记忆化搜索 | 状态数乘以单状态转移成本 | 缓存占空间，递归深度仍受限制 |

已有的 `../STLs_PY/` 更侧重 Python 容器的完整操作；本目录更侧重算法题中的标准库组合和可复用模板。

## 官方文档

- [datetime](https://docs.python.org/3/library/datetime.html) / [calendar](https://docs.python.org/3/library/calendar.html)
- [collections](https://docs.python.org/3/library/collections.html) / [heapq](https://docs.python.org/3/library/heapq.html)
- [bisect](https://docs.python.org/3/library/bisect.html) / [math](https://docs.python.org/3/library/math.html)
- [itertools](https://docs.python.org/3/library/itertools.html) / [functools](https://docs.python.org/3/library/functools.html)
