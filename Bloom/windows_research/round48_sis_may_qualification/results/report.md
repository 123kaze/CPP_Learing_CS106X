# Round48：SIS五月固定前缀资格审计

真实线上来源不等于已经证明RA需要或有优势。本轮只做资格，尚未测方法FP/SQL时间。任务是observed-success vs404的回溯稳定请求target子集，不从HTTP200推出真实业务record存在性。

## 输入范围

- 原五月文件13687894566B；官方MD5通过，仅提取五月。
- 按预声明读取前2000000原始行；实际2000000行、1946580个成功解析GET。不是全月。
- 时间范围2018-05-23T04:32:03+02:00至2018-05-23T12:33:25+02:00；回退144次，未按time重新排序。
- HTTP状态计数：`{"200": 938276, "206": 228, "301": 708, "302": 48844, "304": 934477, "400": 10, "404": 9940, "416": 1, "499": 14089, "500": 7}`。认证/重定向/5xx不当negative。
- 稳定members=140493，negativekeys=211，稳定404requests=9940，404保留率=1.000000。
- 冲突keys=0，排除冲突404=0。

## 资格结论

进入后续方法矩阵：False。
不合格原因：['negative_keys<1000', 'retained_404_requests<10000', 'seed4801:train_negative_keys<20', 'seed4801:validation_negative_keys<20', 'seed4802:train_negative_keys<20', 'seed4802:validation_negative_keys<20', 'seed4803:train_negative_keys<20', 'seed4803:validation_negative_keys<20']。

| seed | 开发AUC16 | learning negatives | tail negatives | 特征重叠比例 | learning重复比例 | firstcomponent规则拒绝tail | two-components规则拒绝tail |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 4801 | 0.011730826767727137 | 1957 | 7869 | 0.200000 | 0.971385 | 2 | 5 |
| 4802 | 0.12322865428904495 | 1971 | 7944 | 0.207071 | 0.967529 | 2 | 5 |
| 4803 | 0.14037471192420406 | 1973 | 7906 | 0.202020 | 0.967562 | 2 | 5 |

Cheap-rule packed支持表的payload/header另见data.json，未计时也不保证可在小预算中免费使用；其支持集合来自同一静态member目录。若规则已排除大部分negative，不能把分类AUC直接当必须部署模型的证据。

目录/冲突判定使用整个选定prefix，所以是回溯稳定子集；querystring保留为精确key，不输出userid/client/referrer/useragent。原系统200登录页/业务错误仍可能返回successstatus，仅凭access log不能建立真实KV对象存在性。原IP及身份字段不训练、不发布。

没有看方法FP后换月/扩窗/降低门槛，六月等月仍未提取/解析。失败资格不等于RA输了或赢了；不要把未运行的五方法/端到端实验写成完成。论文未动，本批未push。
