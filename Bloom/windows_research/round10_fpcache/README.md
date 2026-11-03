# round10_fpcache：不用成员索引的 64 位指纹缓存

回应审稿意见"缓存插入要查成员哈希索引，索引不在预算内"。冻结的 RA6 不改，只把引擎用的缓存模块换成 `src/cache_fp.py`：每个条目存 64 位哈希指纹，完整匹配才算命中，插入不查索引。

- `src/cache_fp.py`：指纹缓存，除条目格式外与 `round5_dp/src/cache5.py` 相同（分桶、4 路 CLOCK、打包数组、字节记账）。
- `src/test_cache_fp.py`：与 cache5 的逐计数等价检查（F = 40、安全长度全为 40）、字节记账、假阴性。
- `src/run10.py`：第六轮主表的全部案例，用指纹缓存跑 RA6 → `results/main/`。`--cache index` 换回原缓存，用于回归检查（逐行复现第六轮，`results/check_index/`）。
- `src/decompose.py`：同一个结构、同样字节下比较三种缓存（带索引 / 完整 40 位 / 64 位指纹），区分"前缀泛化"和"槽位变少"两种作用 → `results/decompose/`。
- `src/report10.py`：生成 `results/report.md`。结论：`results/结论.md`。

```bash
cd windows_research/round10_fpcache
../../.condaenv/bin/python src/test_cache_fp.py
src/run_all.sh && src/run_decompose.sh && ../../.condaenv/bin/python src/report10.py
```

两组任务各约 40 分钟（4 个并行，峰值内存每个约 1.5 GB）。
