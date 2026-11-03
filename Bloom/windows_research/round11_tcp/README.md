# round11_tcp：协议一致（只用 TCP）的真实轨迹

回应审稿意见"真实轨迹的成员是 UDP、负例是 TCP，key 含协议"。只保留 TCP 包：前一半时间出现过的流是成员，之后才出现的流是负例，查询是后一半的 TCP 包。设计冻结在 `plan/design-freeze.md`，写于看到结果之前。

- `src/tcp11.py`：
  - `prepare`：构造 4 条轨迹（Caida、MAWI 2020–2022）的数据并训练模型，数据和模型写入 round2 的缓存目录，统计写入 `results/datasets.json`；
  - `method <run5|run6|run10|grid10> <dataset>`：在进程内运行冻结的第五、六、十轮脚本，只把输出根目录改到 `results/<m>/`。
- `src/nomodel11.py`：不用模型的对照（纯 BF、BF + 缓存，`--cache fp64` 为指纹缓存）→ `results/nomodel/`，每条轨迹几秒。
- `src/run_all.sh`：全部方法 × 全部轨迹，4 个并行，约 1 小时。
- `src/report11.py`：生成 `results/report.md`。结论：`results/结论.md`。

```bash
cd windows_research/round11_tcp
../../.condaenv/bin/python -u src/tcp11.py prepare
src/run_all.sh && ../../.condaenv/bin/python src/report11.py
```
