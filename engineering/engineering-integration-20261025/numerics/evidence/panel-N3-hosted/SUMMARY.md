# N3 数值诊断：原时限停止，尚无已记录的探针求解

这是 **derived_public_summary**：从已保存、逐成员核验的原件派生，只公开结果与哈希。原 ZIP 与私有完整证据保持原字节；本摘要不包含原始 API、job 日志、进程或环境明细，也不提供私有文件定位信息。

## 实际执行身份

功能源为 C2 **bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb**；独立工作流提交 **b7e53d181ab65338e651eb8d8ecc167dadeb1dfd**。[实际 run 40209098454](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40209098454)，attempt 1，job 121216292574。新 driver SHA256 为 **4f6242e1265a6441cf7812d665c031f38d1d24d60a37fdbd294889d855649092**。

原 ZIP **N3-40209098454-1.zip**，**201,592,456 B**，SHA256 **8e1bdb8cff00d73550f9a6b472cc261b1bdaf688588fc2ef3ec84fca9927c97e**。766 个成员与 765 个 manifest 内容、原 K/C/mesh/loads/points 及五个 RHS/方向的原始列字节已分别由两位读者核验。完整原件已保存于授权的私有证据目的地。

## 结果与资源边界

本次沿用 MMD_AT_PLUS_A、pivot threshold 1、SymmetricMode=False、不缩放、不迭代修正；原 K/b/C、五个原方向与 float64 残差 **1e-7** 不变。相对 N2，本次 AS 由 6 GiB 显式改为 **8 GiB**，形成新的容量研究身份；原监督 **180 秒、shared 6.8 GiB、任务文件系统 500 MiB、单线程** 保持。

原 supervisor 在 **181.076409721 秒**以 `wall_time_limit` 停止，worker exit **-15**；外层 child exit **143**，外层平台时间 cap 未触发。最终 driver report 不存在，最后原进度停于 `original_full_operator_ready`。五 RHS 已保存，五 probe 均 `not_started`：**0 recorded solve / 0 field / 0 residual**，没有记录到因子分解完成。这不属于已评估的残差失败，也不能写作任何探针通过。

采样峰值 RSS **5,694,496,768 B**、HWM **6,530,998,272 B**、VmSize **8,380,502,016 B**，shared nonreclaimable 峰值 **5,935,220,968 B**。VmSize 采样峰不等于 VmPeak；现存 VmPeak 仅来自两个分解前阶段，不能外推整次峰值。实际资源计量范围是 service 及后代，窄于整 VM。

本次未观察到 N1/N2 同一扩容报错，仍不能证明 N2 的唯一原因。保留本次时限失败，不据此自动扩大预算。没有新 H、H-action restore、全域 QP、EP5 结构/公差、G2、实物或制造资格。

`OUTCOME.json` 给出审核过的机器可读结果；`ARCHIVE_REFERENCE.json` 只给原件文件名、大小、哈希、源码与公开 run URL。派生清单和敏感内容检查覆盖本公开目录的允许内容；原始证据未被修改或替换。
