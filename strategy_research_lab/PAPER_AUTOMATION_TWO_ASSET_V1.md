# 两资产纸面初始化守护（已安装）

安装时间：2026-10-12。macOS 用户级 LaunchAgent
`com.byte.strategy-research-paper-init` 已加载，定义文件位于：

`/Users/bytedance/Library/LaunchAgents/com.byte.strategy-research-paper-init.plist`

它每 15 分钟调用一次 `paper_initialize_watchdog.py --once`，但脚本有不可绕过的时间门控：

- 仅在 **2026-10-13、上海时间 16:00–21:59** 尝试数据源；
- 仅当 510300 与 518880 有共同日线时，才执行
  `paper_two_asset_tracker.py --as-of 20261013 --commit`；
- 该命令只写 `paper_two_asset_v1_state.json` 和 `paper_two_asset_v1.csv` 的虚拟交易；
  **不会调用券商 API、不会发送真实订单**；
- 已初始化时不再写入；目标日之后也拒绝按已知价格补录。

标准输出与错误日志：

- `paper_initialize_watchdog.stdout.log`
- `paper_initialize_watchdog.stderr.log`

检查状态：

```bash
launchctl print gui/501/com.byte.strategy-research-paper-init
tail -n 20 paper_initialize_watchdog.stdout.log
```

若以后需要停止这个**纸面**守护，可显式执行（不会影响任何真实持仓）：

```bash
launchctl bootout gui/501 /Users/bytedance/Library/LaunchAgents/com.byte.strategy-research-paper-init.plist
```

守护逻辑有离线单元测试，覆盖目标日前、收盘窗口外、目标窗口内和账户已初始化的情形。它只是
确保不漏掉前瞻纸面建仓，不能保证数据源准时发布、策略获利或真实市场成交。
