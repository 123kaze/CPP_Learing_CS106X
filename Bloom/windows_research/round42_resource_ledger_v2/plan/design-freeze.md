# Round42v2：资源字段独立修正，不重测查询

2026-11-23。事后发现：Round42 worker的preparation.feature_matrix_bytes使用sys.getsizeof(X)，X是非owning ndarray视图，仅记128bytes，漏底层3153200bytes payload。旧代码/JSON/计时/报告不修改。

新源码、输入SHA冻结后，读取3个旧worker、63行resources_and_latency.csv及round36 NPZ；核验3个旧字段均128、同一输入X形状dtype；沿ndarray.base链按对象identity去重计量物理payload/header。报告logical payload、view shallow bytes和retained backing chain bytes，不重复计payload。不把这个局部链大小称为完整harness RSS。

生成3行特征账本、63行添加更正字段的资源/延迟表；所有旧列逐字符串相同，保存旧源SHA，标明query_timing_provenance='unchanged_round42_archive'。不重跑SQL、训练或完整实验，不改变FP、Filter内存和回本计算；发现影响其他字段则停止另行报告。

测试：owning数组、non-owning reshape视图、不同字节dtype。只读数据，Python -I，输出拒绝覆盖。此v2专门修输入工作区披露，不声称第42轮变成新独立计时或现代生产KV。
