# Round46：DNS日志首次解析失败留档

公开MACCDC2012派生DNS日志下载完成并通过长度/SHA256/gzipCRC：6606969B压缩、62075487B展开，下载及CRC约9.65秒。

原冻结解析器要求Zeek`#fields`表头，但实际是23列无表头TSV，首记录即触发`AssertionError: MissingZeek#fields`。原源码、runner.log、failure.json及原始文件保持，不在这里修解析器或重跑。

另立[格式适配v2](../round46_dns_qualification_v2/README.md)：公开分析笔记提供对应列顺序，再逐行核验qtype/rcode数字与名称一致；只向新派生gzip添加明确header，原body字节和顺序保持。v2完成资格审计，但仅18个稳定正域名，未过事前1000members门槛，不进入方法比较。

来源：https://www.secrepo.com/maccdc2012/dns.log.gz 。SecRepo页面声明自己生成/托管数据默认CC BY4.0，例外另注；底层PCAP许可未单独核验。原始域名/客户端不发布，不下载执行任何malware。MACCDC是安全竞赛/实验环境，不是自然生产DNS。没有把NXDOMAIN线索写成生产系统需要RA的证明。
