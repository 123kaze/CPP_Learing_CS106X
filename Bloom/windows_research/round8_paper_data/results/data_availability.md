# 论文数据可得性审计（2026-11-01）

## 已核实

- 作者官方仓库 `Spatio-Temporal-Lab/LBF-Gama`，主分支提交 `27a454a5d8d61156e443096a262e5d96fdd27b9f`。
- 检查主分支递归树、公开分支 `sy/cod`、`sy/yelp`、`sy/url`、`syy/FastPLBF`、dataset 历史和公开 release：未取得论文 Train/Test/Query CSV。历史数据代码主要是 tweet 处理，不是论文最终 CSV。
- 作者 README 只链接公开原始源。不能从“同源”推出“同样清洗、样本或划分”。

## URL

- 来源：<https://www.kaggle.com/datasets/sid321axn/malicious-urls-dataset>，Kaggle API v1，最后更新时间 2021-07-23，许可 CC0。
- 原始 CSV 651,191 行，223,088 恶意 / 428,103 良性；论文表1为 223,088 / 428,118。负例差15行，不补齐假数据。
- 官方 `embedding_gene/url_embedding.py` 生成 10 维特征，640,106 行（212,691 / 427,415）；同归一化URL的29个多标签冲突共58行被单列剔除，最终 640,048 行（212,662 / 427,386）。
- 特征依赖经用户批准安装到隔离 deps 目录，不改既有环境；tld 0.13.2、tldextract 5.4.0。suffix 使用安装包离线 snapshot，不访问查询 URL。
- 精确处理/划分未得到：该结果标记 `public_source_reconstruction_not_exact_paper_split`，不标“论文数值精确复现”。逐项SHA256和计数见 `paper_url_data_audit.json`（由报告生成器从数据审计导出）。

## COD

- 来源：<https://www.kaggle.com/datasets/hari31416/celestialclassify>，v1，2023-04-02，许可 CC0。
- Kaggle 文件API报告 train.csv 2,058,444,368 B；test.csv 1,029,217,422 B，本机文件大小一致；数据预处理时计算SHA256。
- 本机原始600万行（300万 galaxy / 300万 star）。论文表1为2,498,077 / 2,980,291，筛选/划分未公开，不任意抽样凑数。
- 论文历史 COD 脚本把 objID 留在输入里；本轮明确把它作为key并排除出模型特征，不能称该输入与未知论文最终特征完全等价。

## Yelp：阻塞

- 官方来源：<https://www.yelp.com/dataset/download>。当前公开网页访问返回403。
- 作者 `model_generate_yelp.py` 依赖处理后的 train/test/query CSV、关键词和区域 embedding；`lib/data_processing.py` 还引用负例生成结果。官方仓库未提供这些最终输入。
- 论文描述过滤稀疏区域，但没有足够资料重建384,602正例/249,886负例及对应embedding。不能用“评论星级分类”或其他Yelp数据冒充。
- 当前不下载或接受未获用户授权的许可证协议，也不联系作者。精确Yelp/论文划分需要作者提供最终数据资产或用户已获许可的本地文件。

## 比较归属

- 论文表2/3是G-LBF，G-PLBF对应第7页图7的192KB。原来的24KiB流数据对比不是论文实验复现。
- 本轮测量G-LBF/G-PLBF/RA6，数据条件和实际预算/索引差异全部分列；原样脚本失败不计“FPR=0”或“胜出”。
