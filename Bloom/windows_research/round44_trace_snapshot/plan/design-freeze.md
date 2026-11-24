# Round44：真实Twitter请求驱动的检查点去重目录——资格与五方法协议

2026-11-23。用户明确授权继续。**B类证据：真实轨迹驱动的构造任务，不是Twitter原生产KV后端NotFound实验。** 不修改论文、旧冻结代码、旧标签，不自动push或启动子agent。

## 数据来源与固定选择

Twitter/cache-trace，公开CC BY4.0。固定upstream commit1c503676d6972d4394a360e09162149a6c00f516（2020-11-10），固定samples/2020Mar/cluster001、cluster002、cluster003，按名称顺序取前三个，不根据内容/方法效果换cluster。

- cluster001:81189662bytes，Git blob SHA1 fc5d8a10f9aed97e2f75b0b57db66e734d2bbbdb
- cluster002:44555350bytes，b6119bbbc6b07301d8e11f01aadae0e78e1f4f99
- cluster003:40207548bytes，52abd1be4459656945bc1e3c5052570d7f75c9aa

合计165952560bytes；每份最大128MiB。每文件下载到新建空输入目录，curl HTTPS、最多300秒、无自动重试；顺序下载，验证长度、Git blob SHA1与SHA256；保留headers/log/error。不解包、不执行文件。解析程序放src，Python -I；原始匿名key/客户端字段不发布，结果只公开聚合及hash。公开页面未说明sample提取/排序方式，不称为完整无采样原始周。保留文件记录顺序，报告时间回退；不排序制造局部性。

## 明确任务语义

去重/曾见key静态检查点：只保留get/gets请求，使用CSV中完整匿名key bytes作精确请求身份。前25%GET序列中出现的全部key构成不可变目录M。后25%–50%GET序列是learning，后50%是tail。**目录只用早期前缀，绝不用全日志未来成功来补目录；之后出现的新key不加入这个固定检查点。** 后续请求查询“该key是否属于检查点目录”，并非“原生产数据库现在是否存在”。精确set/SQL可给出任务真值，无需猜cache hit/miss。写请求不用于扩大M；本轮不是动态seen-ever在线集合。

不使用value size=0、TTL、原cache misses、client id、原GET返回值来判membership。构造task在去重/静态快照检查中有实际含义，但不能据此宣称原生产服务需要RA，或真实NotFound比例等于这里的negative比例。

## 解析与特征

标准7列CSV：timestamp、anonymized key、original key size、value size、client id、operation、TTL。只把timestamp/key/key size/operation用于解析和诊断；客户端不保留、不反匿名化。记录最大64KiB、每文件最多2000000行；若格式不匹配、嵌入换行/键为空/数值非法则失败留档，不临时修正式协议。全样本其他操作计数保留。完整匿名key必须UTF8/ASCII兼容bytes，字典去重不使用64bit压缩ID代替key。每key的original key size若变化，记录count但不作为模型输入，避免未知一致性协议。

query特征只由匿名key自身计算，固定24维：长度；冒号/斜杠/点/下划线/连字符/等号/百分号/问号/与号计数；数字/大写/小写计数；按[:/_\\-.]切分的token数/最长token/最短非空token；开头连续字母数/开头连续数字数；结尾连续字母数/结尾连续数字数；首/尾字符是否数字；字母总数比例；数字比例。不开字典lookup特征，不输入membership/时间/未来频率/client/响应值/随机hash数值；没有语义词表训练。

key转SHA256前64bits仅为旧BF引擎哈希输入（有限集合唯一性assert），**不是精确负cache身份**；严格缓存采用round41完整raw-key Exact128，超长key不插入。因数据key匿名化，可学习性仅说明匿名化后保留结构，不代表原始语义还全部可用。

## Split和资格（方法FP之前冻结）

seeds4401/4402/4403。所有M均插入BF，随机50%member作模型训练。负train/val仅来自learning窗口首次出现的新key，按独立hash10%/10%分配；剩余80%与tail首次出现新key为query pool。目录查询的自然member请求保留；negative训练/验证key请求在learning/tail评估中剔除并报告比例，不偷换原顺序。无外部原标签泄漏，因为真值是已冻结目录中的精确membership。

语义/规模门限：members>=1000、distinct negative>=1000；每seed负train/val各>=20、learning/tail评估negative各>=1000；确认目录仅从前缀、split互斥、所有保留key原始字节一致。任一不满足则该固定cluster不进方法矩阵，不换cluster。

AUC、特征重叠、学习重复率、region重复差另作**解释诊断，不是方法继续门限**，合格规模下的弱模型控制也全部运行。固定16tree开发AUC（heldout members+neg_val）、按neg_val score五分位区域及learning重复差，参考AUC>=.70/重叠>=.01/重复>=.10/两区各50distinct且gap>=.10但无论是否满足都保留。

## 五方法与对照

仅语义/规模合格cluster，每3seed×3预算：ceil(n*{2,4,8}/8192)KiB，至少4KiB。200tree/31leaf/lr.1/单线程；原14tree/13fraction网格，GT19、RA6 top5，H=实际预设tail negative长度。明确新Exact128 cache布局，不给原RA6/fp64保证追认。scope绑定E5.K为exact41模块并恢复，不改冻结文件。

Gama、Replay、RA-global、RA6-Exact128、BF+Exact128、PlainBF、ZGate-Exact128，同Filter Budget，模型/BF/cache/路由/header全部计费，额外成员索引0。ZGate只看learning，tie选BF，收两类搜索+回放成本。所有cold tail完整回放；对所有member做静态BF及最终cache0FN核验。每个method相同流，不按tail选配置。

额外cheap-rule诊断：若某key长度在M中从未出现，可严格拒绝；只计直接length支持规则，不假称它是完整可学习基线。namespace语义不统一，因此不猜一个分隔符充当真实命名空间规则。记录规则可拒绝的negative数，避免把显而易见的长度捷径当模型创新。

## 时序与归档

先冻结下载程序和本协议，下载三份固定文件；完整解析/诊断/模型比较源码必须在首次解析数据前第二次冻结（download freeze与source freeze独立）。模型比较不得在资格诊断输出前执行。

每阶段计时：下载、解析/特征/流构造、开发诊断、训练、score/树准备、GT、候选构建/选择、tail replay/成员检查、输入array与RSS。这里回放不是完整SQL延迟，若有合适信号，再另立明确标注的后续在线SQL轮次；不拿round43合成时延套到真实数据。

顺序worker，一native线程，下载单文件300秒、解析/诊断单cluster600秒、方法单cluster/seed1200秒；至少2GiB磁盘、peak RSS4GiB上限事后报告，超限/失败不重启。自动重试0。失败来源/未通过cluster全部留档。原始匿名数据置ignored inputs/cache，最终发布不含客户key/client信息。许可作者/来源和修改说明保留。
