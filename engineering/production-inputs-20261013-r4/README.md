# 实际生产输入修正 R4

系统容量目标为4700mAh，A优先较大电池；A、B容量和所选电池均未实物冻结。新请求纠正R3将4700mAh错误标成A容量的字段，R3历史原文保留但已由本请求替代。

本轮直接检索厂家原始资料，新增文件分别保存在OLED、FPC、PCB和检测器R4目录。维修原理图、厂家参考设计、动态柔性线路设计手册和目标模组的受控生产资料必须按适用版本使用；任一单项文件不能替代完整装配和实物资格。

`targeted-controlled-input-request.json`仅是待发送的技术请求，无外发、NDA或订货。`manufacturing_go=false`。

实际独立反例与修复复核分别为 `proof-manual-rearm-counterexample.json` 和 `proof-manual-rearm-repair-check.json`。前者在WDI仍卡高时，t=700ms人工重置后错误许可为true；修复后同一路径的卡高、卡低均为false。两份报告分别绑定当时模型SHA；它们不代表实物时序或主负回线资格。

Hirose补强输入解释：图纸的最低0.1mm与guideline推荐至少0.2mm不是逻辑矛盾，0.2mm可同时满足两者。两种规则的角色应保留，不能仅凭此差异新增制造阻塞；本项目尚缺实际应力释放、锚夹、装配和资格证据。
