# 资格输入来源更新（首次解析/资格源码冻结前）

原单线程extract48在1200秒超时，留下670424758B partial，原failure与源码不改。该partial不会输入parser。

用户明确允许四线程/8小时，另立round48_sis_extract_v2输出到新空目录。尚未冻结/运行的data48.py与run48.py现在只接受v2的results/extraction.json中status=verified的完整五月文件，长度及完整MD5/SHA必须经过v2校验。

这只更换数据接入成功回执/路径，数据本身仍是同一官方archive、同一月份、同一预声明前2000000行；不改特征、语义、split或资格门槛。原round48提取不能改写为成功。资格源码将在首次读取真实HTTP记录之前单独冻结，连同此说明及v2回执保存SHA。
