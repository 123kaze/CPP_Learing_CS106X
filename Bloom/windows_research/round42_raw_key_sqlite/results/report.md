# Round42：原始key、完整查询路径与SQLite反馈

189条查询计时，63个字节/正确性/延迟组合，9条学习采集计时。原始请求顺序、不重采样member比例；每seed的固定前200000条eligible mixed-tail请求。不是独立现代生产KV工作负载。

## 完整查询延迟

| KiB | Method | 三seed us/query中位数 | FP中位数 | 前端/索引字节例(seed3601) |
| --- | --- | ---: | ---: | --- |
| 8 | NoFilter | 3.60143 | 3221 | 0 / 0 |
| 8 | PlainBF | 5.16217 | 961 | 8192 / 0 |
| 8 | BF+Exact128 | 5.32797 | 698 | 8186 / 0 |
| 8 | RA6-Exact128 | 9.66296 | 875 | 7798 / 0 |
| 8 | RA6-prefix | 9.71132 | 425 | 7375 / 260760 |
| 8 | DirectHashIndex | 5.14978 | 0 | 260760 / 0 |
| 8 | PlainBF-RAactual | 5.13459 | 0 | 268128 / 0 |
| 16 | NoFilter | 3.62417 | 3221 | 0 / 0 |
| 16 | PlainBF | 5.07322 | 436 | 16384 / 0 |
| 16 | BF+Exact128 | 5.45029 | 198 | 16377 / 0 |
| 16 | RA6-Exact128 | 9.71668 | 225 | 15797 / 0 |
| 16 | RA6-prefix | 9.69395 | 128 | 15487 / 260760 |
| 16 | DirectHashIndex | 5.18736 | 0 | 260760 / 0 |
| 16 | PlainBF-RAactual | 5.20801 | 0 | 276240 / 0 |
| 32 | NoFilter | 3.65182 | 3221 | 0 / 0 |
| 32 | PlainBF | 5.15910 | 25 | 32768 / 0 |
| 32 | BF+Exact128 | 5.42775 | 19 | 32765 / 0 |
| 32 | RA6-Exact128 | 9.77735 | 23 | 32048 / 0 |
| 32 | RA6-prefix | 9.86864 | 14 | 31804 / 260760 |
| 32 | DirectHashIndex | 5.30670 | 0 | 260760 / 0 |
| 32 | PlainBF-RAactual | 5.28183 | 0 | 292560 / 0 |

上述先每case取3次中位数再按seed汇总；配对方法比值在summary中另算，不能用列中位数相除替代。计时包含raw hash、按需原词法特征、模型、BF/cache、真实SQL、按需safe-prefix搜索与插入；NoFilter不算无用hash/特征。所有方法严格静态zero-FN；prefix需完整同版本索引，exact存完整≤128byte键、超长不缓存。DirectHashIndex拒绝hash不存在，hash相同仍查精确SQL。

## 学习标签采集（seed3601，16KiB）

| Arm | queries | backend calls | seconds median | negative counter bytes |
| --- | ---: | ---: | ---: | ---: |
| forced_all | 773833 | 773833 | 2.740511 | 230394 |
| certified_existing_BF10 | 773833 | 762669 | 4.170357 | 230394 |
| existing_BF10_no_logging | 773833 | 762669 | 4.220003 | None |

完整入口计数保留被filter拒绝的请求；收集标签逐项等于精确backend真值。同一个现成BF的认证拒绝/精确cache命中可以提供negative标签，额外lookup调用为0；日志计数CPU与内存仍付费。此原型验证采集协议，不是动态更新、并发在线重配置或训练管线已接入生产的证明。强制所有请求查backend作为不同学习协议保留。

## 构建和回本边界

resources_and_latency.csv列出逐方法训练/特征/score/选择/部署数组重建/索引的accounted startup；共同数据库创建、输入加载、JIT/验证另列，不与query混算。模型训练与候选score仍使用原实验离线pool，pool范围准备成本是该可复现实验的账本，不宣称最优在线实现。break_even.csv只在观测query成本有正收益斜率时给出外推；否则明确无持续回本。此表假设已有共享标签，不能与需要新标签采集的情境混为一谈。

字节表计数组payload/header与实际索引，不含整个Python解释器、common SQLite/OS page cache或harness持有的全局key列表；后者与RSS单列。临时SQLite DB在退出后清理。数据库不远程、不并发、不加人工等待；大多数查询可能为members，不能用只看negative流的收益解释全部混合延迟。

不是individual p50/p99；这些是完整窗口wall/N。3次计时及3seed共享同一日志，不作独立样本或显著性声明。全量negative FP看第41轮，本轮短窗口FP不可替代它。
