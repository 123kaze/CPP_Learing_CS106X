# learned + adaptive 混合过滤器：可行性实验

问题：learned filter（PLBF）里由模型直接放行的那部分误报，能不能靠误报反馈来修正？在模型、backup 过滤器和修正结构之间应该怎样分配内存？

当前结论和下一步见 [docs/决策记录.md](docs/决策记录.md)。

## 目录

```
learned_adaptive_hybrid/
├── README.md                    本文件
├── docs/
│   ├── 问题定义.md               论文要解决的问题、贡献点、核对注记与待验证实验设计
│   ├── 决策记录.md               每轮实验后的判断与下一步（按日期追加）
│   └── 定理草稿.md               上界 / 下界 / 前缀长度引理
├── src/
│   ├── common.py                数据集（COD、Caida）、48 树模型、BF/AQF/PLBF/负例缓存、查询模拟器
│   ├── exp1_fp_source.py        实验 1：朴素混合的剩余误报来源（COD）
│   ├── checks.py                三项核对（查询池不相交、4MiB 原始计数、对抗负载口径）
│   ├── exp2_repetition_cache.py 实验 2（COD）与实验 3（Caida，传参）：重复程度 × 负例缓存
│   ├── exp4_cache_policy.py     实验 4：FIFO / LRU / oracle-LFU / OPT × 缓存比例（Caida）
│   ├── exp5_mismatch.py         实验 5 预览：离线选比例在负载错配下的代价（用实验 4 的结果）
│   ├── exp6_split_hybrid.py     实验 6：分工型混合（PLBF+AQF+放行区缓存）与成员比对成本（Caida）
│   ├── exp7_cache_size_rule.py  实验 7：部署前可算的缓存大小规则（COD / Caida / Shalla）
│   ├── exp8_cap_and_neff.py     实验 8：上限的模型推导（Zipf + TOP-k / Che-LRU）与 HLL 估 N_eff
│   ├── exp8b_model_neff.py      实验 8b：HLL 估出的 N_eff 直接代入模型
│   ├── exp9_fp_stream_controller.py 实验 9：误报流模型、只增不减控制器、真实轨迹（caida_flow）
│   ├── exp9b_sensitivity.py     实验 9b：8b 模型对偏斜度范围和 Q 的敏感性
│   ├── exp10_baselines.py       实验 10：与基线对比（PLBF、TODS-CAF、SkiQF 式准入、纯 AQF/SkiQF、learned stacked）
│   ├── exp11_original_baselines.py 实验 11：原版 Stacked（Deeds 等人 C++）与原版 Gama（模型大小搜索）
│   ├── exp12_gama_cache.py      实验 12：Gama＋缓存（Gama 是 r=0 的特例）；报告合并实验 10–12、含高预算
│   ├── exp13_deployable.py      实验 13：只用学习期测量的可部署版本；控制器的阻尼 / 阈值修正
│   ├── exp14_warm_controller.py 实验 14：控制器从学习期校准的结果出发（离线校准＋在线补充）
│   ├── prepare_mawi.py          MAWI tcpdump 文本 → 与 caida.csv 同格式的 CSV（第二条真实轨迹）
│   ├── validate_aqf.py          抽象 AQF 与作者 AdaptiveQF 的对照
│   ├── bench_cache_overhead.py  负例缓存的查询开销
│   └── plot_figures.py          从 results/*/rows.json 画 figures/ 下的全部图
├── results/                     每个实验一个子目录：结论.md、report.md、rows.json、meta.json、run.log
│   ├── exp1_fp_source/
│   ├── checks/
│   ├── exp2_repetition_cache/
│   ├── exp3_caida_working_set/
│   ├── exp4_cache_policy/
│   ├── exp5_mismatch/
│   ├── exp6_split_hybrid/
│   ├── exp7_cache_size_rule/
│   ├── exp8_cap_and_neff/       （含 8b 的 report_b.md）
│   ├── exp9_fp_stream_controller/
│   ├── exp9b_sensitivity/
│   ├── exp10_baselines/
│   ├── exp11_original_baselines/
│   ├── exp12_gama_cache/
│   ├── exp13_deployable/
│   ├── exp14_warm_controller/
│   ├── real_traces/             真实轨迹（Caida 流、MAWI 2020）汇总结论
│   ├── validate_aqf/
│   └── bench_cache_overhead/
├── figures/                     fig1–fig15，编号按实验顺序
├── external/                    （不进 git）
│   ├── How-to-Train-Your-Filter/  论文 benchmark 仓库（含 Caida/URL 等数据，解压在 data/raw/）
│   ├── aqf_port/                  AdaptiveQF 的 ARM 移植副本 + aqf_driver.c
│   ├── stacked_port/              原版 StackedFilter 的驱动 + 头文件兼容副本（patch/）
│   └── mawi/                      MAWI 轨迹的 tcpdump 文本与转换后的 CSV
└── cache/                       （不进 git）cache/<数据集>/{data.npz, scores.npz, model48.txt}
```

约定：新实验依次编号为 `src/expN_<名字>.py`，结果放进 `results/expN_<名字>/`，图编号接在后面，并在 `docs/决策记录.md` 末尾追加一节。

## 怎么运行

```bash
cd Bloom/learned_adaptive_hybrid
../.condaenv/bin/python src/exp1_fp_source.py          # 约 4 分钟；首次会读 CSV、训练模型
../.condaenv/bin/python src/checks.py                  # 依赖实验 1 的 rows.json
../.condaenv/bin/python src/exp2_repetition_cache.py   # 约 4.5 分钟
../.condaenv/bin/python src/exp2_repetition_cache.py --seeds 5 --dataset caida --budgets 128,256,1024 \
    --fracs 0.01,0.02,0.05,0.1,0.2,0.4 --pools 1万=10000,10万=100000,100万=1000000,全部= \
    --out exp3_caida_working_set --title "实验 3：Caida 上的重复程度 × 负例缓存（误报工作集可远大于缓存）"   # 约 6.5 分钟
../.condaenv/bin/python -u src/exp4_cache_policy.py --seeds 5     # 约 3 分钟
../.condaenv/bin/python src/exp5_mismatch.py
../.condaenv/bin/python -u src/exp6_split_hybrid.py --seeds 5     # 约 36 分钟（含 AQF 的模拟较慢）
../.condaenv/bin/python -u src/exp7_cache_size_rule.py --seeds 3  # 约 4.5 分钟；Shalla 需先解压 shalla.tar.gz
../.condaenv/bin/python -u src/exp8_cap_and_neff.py --seeds 3    # 约 4 分钟，依赖实验 7 的结果
../.condaenv/bin/python -u src/exp8b_model_neff.py --seeds 3     # 约 1.5 分钟，依赖实验 7、8
../.condaenv/bin/python -u src/exp9_fp_stream_controller.py --seeds 2   # 约 8 分钟
../.condaenv/bin/python -u src/exp9b_sensitivity.py              # 约 2 分钟，依赖实验 7、8、8b
for d in caida_flow cod caida shalla; do ../.condaenv/bin/python -u src/exp10_baselines.py --dataset $d; done   # Caida 约 40 分钟
../.condaenv/bin/python src/exp10_baselines.py --report
for d in caida_flow cod caida shalla; do ../.condaenv/bin/python -u src/exp11_original_baselines.py --dataset $d; done   # 需先编译 stacked_driver
../.condaenv/bin/python src/exp11_original_baselines.py --report
# 高预算（每成员 ≥10 bit）的基线
for x in "cod 4096" "caida 2048" "shalla 4096" "caida_flow 256"; do set -- $x
  ../.condaenv/bin/python -u src/exp10_baselines.py --dataset $1 --budgets $2 --suffix _hi
  ../.condaenv/bin/python -u src/exp11_original_baselines.py --dataset $1 --budgets $2 --suffix _hi; done
../.condaenv/bin/python -u src/exp12_gama_cache.py --dataset cod --budgets 256,1024,4096      # 其余数据集同理
../.condaenv/bin/python src/exp12_gama_cache.py --report
for d in caida_flow cod caida shalla; do ../.condaenv/bin/python -u src/exp13_deployable.py --dataset $d; done
../.condaenv/bin/python src/exp13_deployable.py --report
for d in caida_flow cod caida shalla; do ../.condaenv/bin/python -u src/exp14_warm_controller.py --dataset $d; done
../.condaenv/bin/python src/exp14_warm_controller.py --report
../.condaenv/bin/python src/validate_aqf.py            # 需要先编译 external/aqf_port/aqf_driver（命令见下）
../.condaenv/bin/python src/bench_cache_overhead.py --dataset cod   # 计时请在空闲机器上跑
../.condaenv/bin/python src/plot_figures.py
```

- Caida 数据：`git clone https://github.com/saltsystemslab/How-to-Train-Your-Filter external/How-to-Train-Your-Filter`（本地固定在 c970c34），再把 `data/compressed/caida.tar.gz` 解压到 `data/raw/`。
- Stacked 驱动：在 `external/stacked_port` 下执行
  `S=../How-to-Train-Your-Filter/adaptiveqf/external/StackedFilters; c++ -O3 -std=c++17 -w -include cassert -Ipatch -Ipatch/StackedFilter -I$S/wrapper -I$S/include/StackedFilter -I$S/include/BloomFilter -I$S/include/Optimization stacked_driver.cpp $S/wrapper/stacked_wrapper.cpp -o stacked_driver`
- AQF 驱动：在 `external/aqf_port` 下执行
  `cc -O3 -DNDEBUG -std=gnu11 -w -Wno-error=int-conversion -Wno-error=incompatible-function-pointer-types -Wno-error=implicit-function-declaration '-Dposix_fallocate(fd,off,len)=ftruncate((fd),(off)+(len))' -I. -Iinclude -I../../../.condaenv/include aqf_driver.c src/{gqf,gqf_file,hashutil,partitioned_counter,exp_utility,rand_util,ll_table}.c -L../../../.condaenv/lib -lcrypto -lssl -lpthread -lm -Wl,-rpath,$PWD/../../../.condaenv/lib -o aqf_driver`

- 原始数据：`Bloom/LBF-Gama/dataset/raw/cod/{train,test}.csv`，从 Kaggle `hari31416/celestialclassify` 下载，不需要登录：`https://www.kaggle.com/api/v1/datasets/download/hari31416/celestialclassify`。
- 环境：`Bloom/.condaenv`，用 conda-forge 装了 python 3.12、numpy、pandas、lightgbm、numba、matplotlib。pip 版 lightgbm 在这台 Mac 上缺 libomp，所以没用 pip。

## 口径

- 成员是 300 万 galaxy，非成员是 300 万 star。按 objID 哈希切分：训练负例 160 万，验证负例 40 万（只用来估计 PLBF 各分段的负例比例），测试负例 99.96 万（所有查询都从这里取）。三者两两不相交，见 `results/checks/checks.md`。
- Caida：key 是包序号 `No.`，UDP 为成员、TCP 为非成员，负例按哈希切成训练 10% / 验证 10% / 测试 80%。
- Shalla：URL 字符串的 64 位哈希作 key，黑名单为成员，Umbrella 域名为非成员，特征见 `common.url_features`（仿作者 vectorize_url），切分同 Caida。
- 缓存默认 LRU（实验 4 之后）；FIFO 只作对照。
- caida_flow：同一份 Caida，key = (源, 目的, 协议) 的流；特征为源、目的、包长均值/最小/最大；查询 = 测试集 TCP 流的包，按时间顺序（`common.load_flow_trace`）。
- 模型是本机训练的 LightGBM，48 树、31 叶，内存按 48×700B 计入预算。它**不是** Windows 那边的 48 树模型，预处理也没有对齐原文。
- AQF 是抽象实现：每槽 r+3 bit，负载 0.95，另留 5% 预留槽给扩展用，预留槽计入内存；没有计入反向映射的成本。
- 负例缓存：每条记录取与全部成员都不冲突的最短前缀，再加 6 bit 长度字段，实测约 27.5–29 bit/条，FIFO 淘汰。
- BF：每个探测位独立混合（`common.bf_pos`）。早期的双重哈希实现有缺陷，已修复并重跑，见决策记录。

## 运行注意

- 长任务请在前台或用会保持前台优先级的方式运行。用 `&` 挂到后台后再退出 shell，macOS 会把进程当成低优先级任务，放到能效核上调度，速度可能慢 5–10 倍。
- Mac 合盖或长时间闲置会休眠并暂停进程，可以用 `caffeinate -s -i -w <pid>` 保持唤醒，直到该进程结束。
- 等待实验结束时，检查结果文件是否已生成，不要用 `pgrep -f <模式>`：等待循环自己的命令行也包含这个模式，会一直匹配到自己，永远不结束。

## 真实轨迹：MAWI

```bash
# 只下载开头 250MB（约 1000 万个包）；MAWI 服务器会限速，下载可能很慢
cd external/mawi
curl -s -r 0-250000000 -o mawi2020.gz https://mawi.wide.ad.jp/mawi/samplepoint-F/2020/202004081400.pcap.gz
gunzip -c mawi2020.gz > mawi2020.pcap            # 截断的尾部会报错，可忽略
tcpdump -r mawi2020.pcap -nn -q -tt -c 10000000 > mawi2020.txt   # 注意：从管道读（-r -）在本机不工作
cd ../..
../.condaenv/bin/python src/prepare_mawi.py external/mawi/mawi2020.txt external/mawi/mawi2020.csv
# 之后数据集名为 mawi2020_flow，实验 10–14 的脚本都可以直接用 --dataset mawi2020_flow
```

MAWI 2021（`mawi2021_flow`）的配置已经登记好，下载 `2021/202104141400.pcap.gz` 的前 120MB 后按同样步骤处理即可。
