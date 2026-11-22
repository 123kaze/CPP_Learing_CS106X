# Round40：fp64概率保证的前提审计

2026-11-22。**这是事后正确性审计，不是未见数据预注册。** 在整理审查回应时，已经检查到共享哈希/条件入缓存的问题，并做过精确分数探索。此处冻结的是可复核的证明与小规模穷举程序，不制造新的真实负载结果，不修改任何旧冻结源码或结果。

## 要核对的断言

旧cache_fp.py注释以及后续报告使用过每member-query `S/2^64` 界。通常这个界要求目标查询指纹在给定缓存内容时具有适当的独立均匀性。仅有非恶意输入和理想哈希，不自动给出这一条件：当前BF的probe和fp64 cache都依赖h1，且只缓存BF放行、backend确认不存在的负key。

## 精确概率反例

考虑不同的原始keys，先固定64个member keys和5个nonmember queries，再以理想随机哈希映射到U=2^b个fingerprint值。原始query keys确实不是members；后端按原始身份精确确认不存在，不能把fingerprint当精确backend key。

- BF为64 bits、64个members、1个probe；冻结baseline.allocate对此参数实际选择k=1。
- BF probe是fingerprint的一个双射变换再mod64。冻结bf_pos的64-bit加法、xor-right-shift和奇数乘法都是双射，因此对均匀fingerprint，probe位置均匀。
- cache为一个4-way桶、4个完整fingerprint slots，起始为空。
- 若5个负查询中至少一个fingerprint与指定member相同，且至多4个查询能通过BF，那么此member的fingerprint必定入cache且不会因容量而淘汰；接着查询这个member就会FN。
- 若BF接收率为p、a=1/U，这个充分事件的概率为`1-(1-a)^5-[p^5-(p-a)^5]`。
- 将p=K/64对64个member均匀probe形成的占用格数K取精确期望，可用占用问题的阶乘矩与Stirling数计算E[p^r]，r=1..4。其64-bit结果严格大于4/2^64；不用Monte Carlo或条件挑选特定member哈希。

同时用更小的b=2、m=4、n=2、S=1、N=2模型穷举全部256种成员/负查询fingerprint赋值，核对通用无淘汰事件概率计算及实际FN；这个小模型不是64-bit实测碰撞。

## 不应夸大的结论

- 反例针对一般原始key压缩成共享fingerprint的保证口径，不代表现有数据已发生64-bit碰撞。第38/39轮的有限样本FP/FN结果不变。
- 若应用的精确key域本来就是uint64，且使用双射编码，完整64-bit cache可以是精确key cache；这不同于把任意字符串压缩到64 bits。对同一个已压缩64-bit值再次加盐/混合不能恢复丢失的信息，也不自动得到两个独立原始key哈希。
- Verified-prefix遇到无法排除member的完全hash别名时bypass，静态完整索引下的zero-FN保证不受此概率界问题影响。
- 可用的保守替代：若成员集合及Q个不同negative原始keys在哈希前固定，理想均匀指纹下，对某固定member跨该有限集合的碰撞事件可用min(1,Q/2^64)界；对全部n members为min(1,nQ/2^64)。这不是无限期/敌对key保证，也不是当前数据观察到的错误率。
- 若要容量型S/2^64保证，需要另外建立查询指纹与缓存选择过程的条件独立性，例如来自原始key的独立cache哈希和相应协议；该变体本轮没有实现，不将其保证追认给共享hash实现。

输出：精确分数及浮点摘要、256状态穷举、冻结原语参数核对、保证修订建议；无大型实验、无生产访问、无论文修改。
