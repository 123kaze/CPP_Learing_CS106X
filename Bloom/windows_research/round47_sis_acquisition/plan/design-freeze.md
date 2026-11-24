# Round47：真实线上SIS日志有界接入（先下载/清单/提取资格，不测RA效果）

2026-11-23。用户明确选择下载约3GB线上日志，并同意项目隔离目录中的官方预编译ZPAQ工具；不本地编译、不修改全局系统、不push、不动论文。不得保证正结果或越过数据资格。

## 来源与预选

Charles University真实线上学生信息系统，2018年5–11月combined access logs，Zenodo record3241445（publication2019-06-06），CC BY4.0。文档列METHOD/path/status/size/referrer/user-agent；用户/IP匿名化描述有限，原URL参数与application错误语义需要后续审计。原client/userID/referrer/UA不发布、不建模。

固定文件：https://zenodo.org/api/records/3241445/files/sis-log.zpaq/content
- bytes2995604801
- MD5 8a48f22d0df19fb8d5044e54b66aac6e（来自官方API），另算SHA256
- 原小型README及.md5sum官方metadata已核验，manifest列201805–201811七个月文件。

**本轮预选五月sis-log-201805-anonymous.txt用于第一阶段资格**，其余月份先不提取/解析，不看效果换月。六月暂留作潜在后续时间段验证，不宣称独立应用或预先冻结全部未来方法。

## 预编译工具

Homebrew zpaq7.15 revision1，arm64_sequoia预编译bottle：
https://ghcr.io/v2/homebrew/core/zpaq/blobs/sha256:0d82a2ae7e022957f0f0675433d8e01622f3ce1a42c2cc7c76ce902f3685744c
SHA256=0d82a2ae7e022957f0f0675433d8e01622f3ce1a42c2cc7c76ce902f3685744c，官方API显示runtime dependencies=[]。只用公开registry匿名pull token，不用/输出用户凭据。

单独下载到新空tools/bottle目录，<=10MiB、60秒、无重试，验证SHA后只提取tar内常规bin/zpaq到新的tools/executable目录，拒绝symlink/path traversal。先检查Mach-O架构/动态依赖再调用帮助；不执行数据archive里的任何内容。工具在轮次.gitignore内，不发布binary，不安装brew或系统路径、不运行本地编译器。

## 网络与空间门限

至少24GiB可用磁盘（当前约56GiB）。首次固定4MiB byte-range probe，必须HTTP206且Content-Range/长度准确；只用于带宽/服务器Range验证，不能解析当正式数据。最多120秒，无重试。预测4并发完整下载需<=1800秒（保守只按单probe速度估计，不假设4倍速度），否则停止并报告资源门限，不自动延长。

正式分4个连续range，边界按ceil(size/4)事前计算，最多4下载并发、每块1200秒，curl connect30秒、retry0、max-filesize精确分块大小。每块独立新空目录保存headers/partial/curl log；全部HTTP206/Content-Range/byte size通过后才在独立assembled目录拼成正式archive。验证官方MD5和SHA256，失败保留、不重试、不用partial解析。

预编译tool最多60秒；archive list最多180秒；五月提取最多1200秒、RSS上限4GiB、输出最大12GiB且至少保留8GiB空闲。超限停止留档，不自动重启被终止的任务。先list完整archive元数据，核验选择的文件名称/大小/无路径穿越；超过展开门限不改选其他月、不直接提取所有文件。只在新空cache/may目录提取指定五月文件，校验官方manifest MD5；其余月份不打开。Listing/提取脚本若需根据实际工具格式适配，另立预先记录的source phase，不修改已冻结下载器。

## 后续资格规则（在首次解析五月前另冻完整解析代码）

只做HTTP稳定响应任务，不把200登录页当真实业务记录存在性：初步语义名为“observed successful vs404target requests”，区分认证/授权/5xx/重定向。完整target/querystring保留为精确key，client/referrer/UA不保留；同key正/404冲突整体排除并报告。解析原始前2000000行（或EOF若更短）的固定prefix，明确不是全月；不按FP缩窗/扩窗。

进入方法比较最低门限维持members>=10000、negative keys>=1000、稳定404>=10000且保留率>=90%、每seednegtrain/val>=20、learn/tail negatives>=1000。开发AUC/特征重叠/重复/region差先诊断，方法效果尚未看。若失格，不降门槛，不扩大prefix，失败/不利结果归档。

本轮先保证来源、字节完整性和可处理性。真实线上来源不自动证明该任务需要RA，更不意味着保证最终出现正结果。
