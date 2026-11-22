# Round40：fp64概率保证前提审计（已核验）

**共享BF/cache哈希下，S/2^64不能仅凭“理想、非恶意哈希”作为通用member-query FN上界。** 四项单测、256状态穷举、冻结原语参数核对及精确分数计算通过。

[完整证明与边界](results/report.md) · [精确有理数结果](results/verification.json) · [审计协议](plan/design-freeze.md) · [源码](src/audit40.py)

## 发现的是什么

BF的放行事件依赖member哈希；fp64又只缓存这些被放行、backend确认不存在的负key。缓存内容因此不自动独立于目标member的fingerprint。

一个有效反例：64-member、64-bit、1-probe BF，单桶4-slot cache，5个预先固定的不同negative原始keys，全部原始key用理想随机哈希。精确计算得到某固定member的FN概率**下界**为约`2.2597621e-19`，已经大于`4/2^64≈2.1684043e-19`。计算对完整member哈希分布取期望，不是条件挑选一个有利哈希，也不用Monte Carlo。

数值很小只说明这是便于核验的反例，不能据此估计真实数据库风险大小。问题是原保证缺少前提，而非宣称实际发生了这么多错误。

## 什么没有改变

- **没有发现实际64-bit数据碰撞，没有改写第38/39轮的FP或有限成员0FN记录。**
- **Verified-prefix不受这条概率界问题影响**：完整静态索引下完全hash别名得到safe length65并bypass，不插入不安全prefix。
- 如果精确key域本来就是uint64且编码是双射，完整64-bit cache是精确key缓存；任意字符串压缩为64-bit fingerprint不是这个特例。
- 原冻结实现和注释不静默改写；本轮是明确的事后勘误，不是新的预注册工作负载。

## 可采用的保证口径

容量型界需要另行证明查询fingerprint与cache入选过程的条件独立性。来自原始key的独立cache哈希及配套协议可能建立该性质，但本轮没有实现/计时这个新变体；对同一个已压缩64-bit值再次加盐并不能恢复丢失的信息。

对于哈希前固定的n个members和Q个不同negative原始keys，理想均匀模型下可用某固定member的`min(1,Q/2^64)`、全部members的`min(1,nQ/2^64)`作为保守有限集合碰撞界。不是无限生命周期或敌对key保证。

严格zero-FN系统应使用已验证prefix、精确key缓存（完整计费）或不带负cache的BF，不能把未成立或很小的概率界当成不可能。

```sh
.condaenv/bin/python -I windows_research/round40_fingerprint_assumptions/src/test40.py
```

审计主程序拒绝覆盖已有结果；无论文修改，无大规模新实验。
