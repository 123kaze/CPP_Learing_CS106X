# Round41：完整原始key精确缓存与总辅助内存对照（已完成）

[协议](plan/design-freeze.md) · [117条结果](results/rows.csv) · [报告](results/report.md) · [核验](results/verification.json)

7项单测通过；3个顺序worker；总耗时60.71秒。原始key重建核对3194984条稳定请求、39415个key及旧特征，未发布原始URL/IP。18个第37轮prefix RA/BF结果复现。

## 解决了什么

- 新`Exact128`缓存完整存储长度≤128bytes的key；完整字节相等才命中。更长key不插入，不截断。hash只选择桶，强制hash别名不会让不同key命中。
- 一个owning数组计入key128bytes、长度2bytes、valid/ref2bytes、每桶CLOCK指针、32bytes头部及ndarray header。不存外部key字典指针。
- 静态同版本成员集合、实际backend确认不存在后插入时，cache有严格零FN语义，不依赖概率碰撞界或8*n索引。成员更新仍需失效；不是动态协议。
- 模型/分区/份额网格与GT19不变，但cache容量改变，所以明确是新变体，不继承旧RA6逐位选择或49×主张。RA6的预测尚未单独建模长key绕过；全部结果保留。

## 结果并非普遍支持学习模型

| 比较 | RA胜/平/负 |
| --- | ---: |
| RA6-Exact128 vs Replay-Exact128 | 8/0/1 |
| RA6-Exact128 vs BF+Exact128 | 3/0/6 |
| prefix RA vs 相同实际辅助字节的PlainBF | 0/0/9 |

ZGate9例都在learning选BF；tail与BF9例全平，但相对RA有3例退化。学习选择保证不等于未来不退化。

**额外索引改变系统结论：** ClarkNet32581成员，排序hash数组260760bytes（含header）。同样计入此项后，PlainBF在原完整尾段9例全部0FP；直接hash索引也0FP。后者只在hash不存在时拒绝，hash存在仍须查精确backend，不是假称64bit表示是精确原始key。有限数据0FP不是BF全称无误报。

不能用加1平滑的巨大比值放大这个结果；关键是绝对FP和额外字节。这里只平衡辅助结构，不包括共同数据库记录/索引、OS缓存、训练状态或全部RSS，也不证明把远端索引搬到前端是无成本的。

## 边界

仍是1995年ClarkNet回溯稳定子集，不是新现代生产KV负载。完整负流与自然混合流都回放，成员0FN；这里只计回放，不是完整查询服务延迟，后续第42轮单列。

混合流输入原始key blob、trace、特征及验证数组属于harness。worker为了另测prefix会持有成员索引；Exact128查询原语本身不接受索引。缓存禁用时回放API的空ndarray是测试接口哨兵，不是声称部署还需要一个未计费的缓存。Python解释器/包装对象不纳入旧Filter Budget口径，RSS与数组账本不可混同。

不改旧冻结代码、论文或投稿标签；不因BF更好重选数据、预算或尾段。
