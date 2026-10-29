# Edge189 有限诊断：一个条件源模型通道已闭合

本轮真实结果是：在已保存的原 `[78,375]` 低子叶中，给原 piece332/edge189 的 AABB 增加一个有原件来源的斜向支撑 slab 后，固定 `material_side=0, axis=1, end=0` 通道的全部523个原 piece 均满足原分离判据。独立角点算法和原独立 V6 通道 reader 均核验了保存的证据。

这是已保存累计深度25低子叶**开放内部的条件序列化源模型证明**。它不改判原累计深度24资格，不改判 V9 owned/first-u失败，不更新全帧上界，也不证明 native BREP 误差、当前S4材料对应或连续G2。

## 实际执行与原件

- 原源码 `diagnose_edge189_line_support_r7e_v1.py`：42,780字节，SHA256 `a8a1bb10b2f12c34146b1f998237b3018885ed820d123299ba854dbd73aea52e`。
- 冻结合同 `R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_CONTRACT_V1.json`：47,167字节，SHA256 `19ae738252a9c86815ba28479e8a62b4d7abca67c9a5b97c4fcbd250c3302798`。
- 实际完整报告在 `attempt-1/R7E_EDGE189_LINE_SUPPORT_DIAGNOSTIC_V1.json`；252,352字节，SHA256 `c9a421350ddb2a934707f4d7d2113b1c8e42b5925b9571623a656569ac98f324`。
- 实际生产claim、stdout、stderr、工具退出记录、前后118输入hash、外部读回回执及完整5个变异payload都保留。进程exit0，worker实测1.682883049秒，peak RSS315,944,960字节。工具等待计时与worker内部计时起止不同，两种实测值分别保留。

## 本次具体改善

原完整参数域、identity placement、非零Vz和完整D全部保留；固定法向为 `(1,2,0)`。生产区间法与独立16端点/D角点法得到同一完整三维源box，六端点严格等于原 AABB。原 AABB 自身仍无法分离，加入exact slab和加入τ-expanded slab均得到原code7。τ-expanded情况下的不归一化法向投影余量显示为 `1.3377677353429304e-5`；它不是物理净间隙或欧氏距离。

唯一完整通道按原顺序检查523个piece，两个非轴向证明位于原piece77和新piece332。其余701个carrier完全不动，目标piece的原AABB也保留，只加一个slab。原独立 reader核验523个codes、两处nonaxis、完整channel和闭边界保留语义。

另行假设的τ tube由128个角点独立验证。它的投影被扩张slab覆盖，但整个tube不被未扩张的原 AABB包含；这个真实阴性结果仍为false。新 `B∩slab` 只继续包含原exact Line+D，不冒称整个native/tolerance shell包络。对应OCCT原API可能把tolerance钳在1e−7下限，故原记录也不是native误差或物理不确定度证书。

## 负控与容量

五个预注册负控都在指定阶段拒绝：缩短参数域、Vz置零在原源身份阶段拒绝；错误法向在固定法向阶段拒绝；漏D由16角点支撑拒绝；漏τ由128假设tube角点支撑拒绝。另对实际完整通道证书删除一个code，原独立reader实际拒绝。资源/其他异常不能被误计为这些负控的pass。

本次526个producer piece测试、951个support判据、531个原独立separator调用、304个实际角点记录、22,793个保守validation扣账。validation原始分项可查；算术上界和source序列化字节的额外overcharge不冒称真实比较次数。加上所有既有已登记诊断，本阶段累计82split、176,215 piece-like、390,589 support-like；未重置原账，也没有新split。

原资源公式、60秒/512MiB有限诊断门和4MiB输出门均保留。`memory.current`只观察，不替代原shared_unreclaimable门。118项注册输入和辅助件在运行前后全hash一致。

## 保留的未决与下一步边界

原成本探针的两子pending历史结果、先前correlation/wire阴性、V9真实owned失败及u0、全16条件未通过项均未编辑。该低子保存的有向体积约为 `5.543919268321698e-11 mm³`；没有据此重新计算整帧上界，也没有外推高子或其余同类叶。

下一项只读准备已由root另行指派到新目录，针对原深度24 parent中实际保存的Cylinder blocker。它不属于本次实际运行，本目录封存后不再写入。
