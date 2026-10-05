| **信号名**   | **方向** | **位宽** | **功能描述**                                               |
| ------------ | -------- | -------- | ---------------------------------------------------------- |
| `clk`        | input    | 1bit     | 时钟信号                                                   |
| `rst`        | input    | 1bit     | 复位信号，高电平有效                                       |
| `memtoreg`   | input    | 1bit     | 写回寄存器的数据源选择信号 (0: ALU 结果, 1: 内存数据)      |
| `pcsrc`      | input    | 1bit     | PC 数据源选择信号 (0: PC+4, 1: 分支跳转地址)               |
| `alusrc`     | input    | 1bit     | ALU 源操作数 B 选择信号 (0: 寄存器数据, 1: 符号扩展立即数) |
| `regdst`     | input    | 1bit     | 写入寄存器的目标地址选择 (0: rt, 1: rd)                    |
| `regwrite`   | input    | 1bit     | 寄存器堆写使能信号                                         |
| `jump`       | input    | 1bit     | 无条件跳转指令标识信号                                     |
| `alucontrol` | input    | 3bits    | ALU 运算控制信号                                           |
| `instr`      | input    | 32bits   | 从指令存储器读出的机器码指令                               |
| `readdata`   | input    | 32bits   | 从数据存储器读出的数据                                     |
| `pc`         | output   | 32bits   | 输出给指令存储器的当前指令地址                             |
| `aluout`     | output   | 32bits   | ALU 的运算结果（也用作数据存储器的访问地址）               |
| `writedata`  | output   | 32bits   | 准备写入数据存储器的数据 (GPR[rt])                         |
| `zero`       | output   | 1bit     | ALU 运算结果是否为零的标志位                               |