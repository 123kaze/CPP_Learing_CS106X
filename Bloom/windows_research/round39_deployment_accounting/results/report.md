# Round39：学习期增量成本与有条件回本

本轮是计数回放、资源核算及参数化外推，不是新的SQL/远程服务完整计时。复用第38轮42个matched-H设置，不取误设H中更好的配置。

## 正确的学习成本差分

`ΔL = L_negative - 已部署baseline在学习段的negative后端调用数`。不能把所有学习查询或所有成员访问都算作RA额外代价。成员访问在本批无FN、相同成员集合条件下两边抵消。

| 格式 | 比较 | 设置数 | 尾段调用减少 | 学习＋当前尾段净调用减少 | 净调用持平 | 学习额外调用/L中位数 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| index | ready_plain | 21 | 21 | 10 | 0 | 0.703132 |
| index | ready_fixed10 | 21 | 10 | 0 | 0 | 0.925190 |
| index | shared_labels_selected_cache | 21 | 11 | 11 | 0 | 0.000000 |
| fp64 | ready_plain | 21 | 21 | 9 | 0 | 0.703132 |
| fp64 | ready_fixed10 | 21 | 10 | 0 | 0 | 0.914600 |
| fp64 | shared_labels_selected_cache | 21 | 10 | 10 | 0 | 0.000000 |

ready_plain：学习前已可部署的Plain BF。ready_fixed10：事前固定10% Cache，学习后保持原cache状态进入尾段；不是看当前学习数据选出的份额。shared_labels_selected_cache：两者共享同一次标签采集，再同时冷部署，增量采集为0。历史标签已经存在时增量同样为0，但不等于所有日志都完整/免费。

shared标签行的baseline_learning_backend_calls=L表示共同新在线采集版本；若是已有历史日志，两边新增采集调用均为0，差分仍相同。其他行比较的是“强制全查询后端的新学习者”与现成baseline，不宣称这是唯一可行的在线采集协议。

## 参数化回本，不补造缺测成本

`ΔT(N) = A + ΔL*C/1e6 + N*[d-(1-p)*s*C]/1e6`。A为额外非lookup启动/学习处理/训练/索引/重配置净成本（本轮示例A>=0）；C为基本backend调用成本；d为每总查询额外非lookup处理成本，含模型/特征/cache与按需prefix验证差额；p为成员比例；s为当前窗口每negative query节省的调用数。

只有`(1-p)*s*C-d>0`才有持续收益斜率。否则在非负启动/采集成本下，增大N不会使原本落后的方案自动回本。示例参数见冻结协议及scenario_projections.csv，A/C/d/p均是假设，不是新的实测生产参数；零/负收益全部保留。若周期性重新采集/重建，A与ΔL必须按周期重复计费，不能假定一次启动可供无限期摊销。

backend-call-only的投影忽略新增CPU/启动成本，且假设未来保持观测节省率；它是有条件的理想化参照，不是实际未来最少请求数保证。A=d=0时，学习额外访问与尾段节省同时乘C，单纯提高backend单次成本不会改变按调用数计算的回本窗口。

## 资源与正确性

- resources.csv逐设置列RA、Plain BF、固定10% BF+Cache、学习选择BF+Cache的Filter实占、缺少索引时的辅助索引字节以及二者之和。这个和仍不包括backend数据、OS缓存、输入矩阵或全部RSS。
- index且cache非空时需8*n+array header；Plain BF和fp64不需要该验证索引。若后端已有完整兼容索引，新增字节为0，但索引本身并未消失；原始key有序不意味着hash有序。
- prefix验证必须在实际absent确认后执行，索引必须完整且与成员快照一致。第35轮实际SQL/TCP测过这一流程；本轮使用已确认标签和预计算safe prefixes，只计调用，不把批量预计算时间当逐miss线上开销。
- 静态集合、模型、预处理和路由版本要一致。成员插入或模型/路由改变可能使旧prefix/BF失效，必须协调cache失效及必要重建，不能沿用旧零FN保证。
- 本批member/negative fingerprint集合不相交，cache成员检查0命中。一般键域下fp64仍可能碰撞；严格zero-FN需求且无验证索引时，不能把fp64直接当等价替代，可选择Plain BF，或另行实现并完整计费的精确key cache。后者未在本轮实现。

## 学习状态不保证比原始流小

learning_state.csv按15个dataset/seed列L和D，不把多个预算与两种格式重复当成独立负载。GT19的state_bytes仅计keys+counts=16D；另有rates=8D，三数组payload为24D。与8L原始轨迹payload相比，分别在D/L>1/2、D/L>1/3时更大。这不是含header、Population中间量或RSS的完整峰值模型。
本批15个输入中，16D大于8L的有2个，24D大于8L的有3个。全distinct人工单测验证了2×/3×payload反例。

## 可以缓解但尚未实现的采集协议

若已有严格zero-FN且与当前快照一致的filter，拒绝本身可证明negative，只对放行请求查backend，就有可能在不增加backend调用的前提下取得全入口标签。完整入口日志/计数CPU与内存仍需支付；只取backend日志会漏掉被filter挡住的请求。fp64 cache命中不能单独当严格negative证书。这里是明确的条件性设计建议，不追认旧实验已经用了这种采集方式。

## 可追溯性与未解决项

本轮新做42个学习到尾段连续cache控制、18个ClarkNet纯BF计数和18个ClarkNet学习选cache结果；24个legacy Plain BF与24个legacy学习选cache行复用已核验档案。没有把它们标成全部新执行。
- 168资源行、126差分比较、756显式参数外推均保留。新ClarkNet-index BF+Cache须复现第37轮；fp64是新增补充。
- 这不是第三方独立复现、不是现代KV轨迹、不是动态成员部署，也不证明完整选择器全局最优或固定点收敛。没有修改论文或冻结旧实验。
