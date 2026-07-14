"""
Todo CLI —— Python 标准库实验课综合项目。

整合了 10 个实验所学的内容：
  - argparse: 命令行参数解析
  - sqlite3:  数据持久化
  - datetime:  截止日期和时间
  - logging:   日志记录
  - json/csv:  导入导出
  - pathlib:   文件路径管理

用法:
  python -m todo.cli add "learn Python stdlib" --due 2026-07-20
  python -m todo.cli list
  python -m todo.cli search python
  python -m todo.cli stats
  python -m todo.cli export tasks.json
"""
