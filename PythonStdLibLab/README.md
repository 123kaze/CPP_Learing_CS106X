# Python 标准库实验课

> 目标不是"学完 Python 标准库"，而是学会：**看到一个需求，知道去找哪个库，并能把它用起来。**

---

## 实验列表

| 实验 | 主题 | 核心库 | 产出 |
|------|------|--------|------|
| 01 | 文件和路径 | `pathlib`, `os`, `shutil`, `glob` | 文件分类器 |
| 02 | JSON/CSV/配置文件 | `json`, `csv`, `configparser` | 格式转换器 |
| 03 | 命令行参数 | `argparse` | 命令行 Todo |
| 04 | 日志 | `logging` | 带日志的 Todo |
| 05 | 时间处理 | `datetime`, `time`, `calendar` | 带截止日期的 Todo |
| 06 | 正则和文本处理 | `re`, `string`, `collections.Counter` | 日志分析器 |
| 07 | 数据库 | `sqlite3` | 数据库版 Todo |
| 08 | 并发 | `threading`, `queue`, `concurrent.futures` | 多线程文件搜索器 |
| 09 | 网络和 HTTP | `http.server`, `urllib` | 本地 HTTP 服务 |
| 10 | 测试 | `unittest`, `doctest` | Todo 的测试套件 |
| 终 | 综合项目 | 以上全部 | Todo CLI 完整应用 |

---

## 学习方法

每个实验按以下流程进行：

```
1. 这个库解决什么问题？
2. 它最小可运行例子是什么？
3. 我怎么 import 它？
4. 最常用的 3 到 5 个 API 是什么？
5. 输入是什么？输出是什么？
6. 出错会抛什么异常？
7. 我能不能改造官方例子，做成自己的小工具？
```

每完成一个实验，写一份简短的**实验报告**：

```
库名：
解决的问题：
最小例子：
常用 API：
我踩的坑：
我做的小练习：
```

---

## 使用方式

```bash
# 进入实验目录
cd experiment_01_pathlib

# 阅读实验指导书
cat 实验指导书.md

# 运行配套代码
python file_classifier.py --help
```

---

## 参考资源

- [Python 官方标准库文档](https://docs.python.org/3/library/index.html)
- [Python 官方教程](https://docs.python.org/3/tutorial/index.html)
