# Round45：命名空间/原key size表示探索（完成，未通过开发闸门）

[协议](plan/design-freeze.md) · [36模型开发结果](results/development.csv) · [报告](results/report.md) · [核验](results/verification.json)

明确事后探索：cluster001–003已经看过第44轮tail，本轮只检查开发段表示，不能当新独立验证。固定4表示×3seed×3cluster，16tree模型；原24维开发AUC9/9逐seed复现。4项词表单测通过，总耗时11.19秒。

| cluster | 原24维AUC中位 | 加原key_size | 加prefix词表 | 二者合并 |
| --- | ---: | ---: | ---: | ---: |
| cluster001 | 0.573436 | 0.573436 | 0.559993 | 0.559993 |
| cluster002 | 0.614198 | 0.614198 | 0.608437 | 0.608437 |
| cluster003 | 0.501172 | 0.501172 | 0.521577 | 0.521577 |

预设门限：至少2/3cluster的3seed配对AUC增量中位>=.03且合并AUC中位>=.65。实际0/3满足，**这一表示分支停止**，未降低门限、未测新tail方法FP、未打开预留cluster004–006。

Prefix只由训练distinct keys建立：长度1/2/4/8，每长度top16；固定64onehot。词表单owning数组336Bpayload+112Bheader=448B，需要后续计入模型方案预算，不能免费。原key_size是请求元数据，不是response value_size；没有反匿名化、没有用hash数值当语义、没有用validation/tail建立词表。

这里只说明本次固定表示没有带来足够开发增益，不证明所有命名空间表示都无效。不再用同一已见tail反复调到赢。没有BF/SQL性能胜出结论、没有论文修改/自动push。
