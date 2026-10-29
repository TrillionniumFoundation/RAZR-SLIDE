# R7 后续归档迁移独立读回附录 V1

**两份完整 Near/Far 归档身份保持，五组迁移副本的全部原件可恢复；这次观察未发现新的五组目录对应差异。** 本附录不改已封存 ledger V2，也不重判原有限姿态科学结果。

实际只读时段为 **2026-10-29 01:39:16.148068–01:39:23.043240 UTC**。计划上限为120秒、256 MiB地址空间、4 GiB流式读取及24 MiB输出；实际6.895271秒，峰RSS58,548,224 B，完整流式读取1,925,905,476 B。

## 完整原件保全

两份完整ZIP在读前、读后均与原成功保存回执、原全成员验证归档身份一致，对应文件的Library ID扩展属性也一致。

| 归档 | 字节 | SHA256 |
|---|---:|---|
| Near | 126,771,580 | `711db7175ea364735f337ecc575b7d7ee479df9287d78c7cec08a147120533ae` |
| Far | 127,370,781 | `7bc806653be9c7e70dea0ad195bcf992d899a06d73e170af499d8f7b10804130` |

五组完整选定成员共 **13,357件、1,257,847,799 B**，本次逐成员重新读取ZIP并核对CRC、SHA256及原最终seal。迁移回执所列 **13,347个已回收重复文件、1,252,169,747 B** 全部仍可从这些已核验归档恢复。本读回没有执行恢复、解包、重建或删除。

## 五组实际目录观察

| 目录组 | 迁移前完整文件数 | 本次可见文件数 | 本次可见字节 |
|---|---:|---:|---:|
| Far engineering | 4,689 | 2 | 1,951,132 |
| Near prerequisite-predock | 2,167 | 2 | 931,730 |
| Near prerequisite-stow_tabs_3 | 2,167 | 2 | 931,730 |
| Far prerequisite-predock | 2,167 | 2 | 931,730 |
| Far prerequisite-stow_tabs_3 | 2,167 | 2 | 931,730 |

这五组在上述时段均只观察到原保留的 `ENGINEERING_MANIFEST.json` 与 `EXPORT_SCOPE.json`，其完整字节与原seal一致，前后成员和stat清点稳定。未观察到本次迁移中已删除的路径再次可见，也未观察到新增未登记文件或哈希不符。**五组当前展开目录均不完整**；原件保全依赖完整归档，不能将历史完整展开状态写成当前状态。

这些是本次有日期的观察。此前Near engineering的2359文件观察涉及另一个未扫描、未修改的目录，其历史对应差异继续保留；vtk与Far `.partial` 的既有原因未决也没有由本次结果解决。本附录不作平台或物理因果推断。

## 原科学记录与容量失败

除已登记迁移的两个prerequisite子目录外，Near/Far各 **388个原raw成员**，合 **65,484,389 B**，已双遍完整哈希核对原最终seal。这覆盖保留的顶层factory/readback实际报告、几何、执行合同与相关原记录。全部静态来源、原审阅和ledger V2字节保持不变；没有新CAD、求解、K/H或包络算法执行，也没有改变原科学门。

方法归档首次尝试仍记为真实失败：原入场要求为 **234,881,024 B**，exit code为1，该次没有生成plan或ZIP。失败断言时的可用字节值未被原程序记录，随后读回为0；本附录保留这一精确区分，不补写断言时的测量值。后续迁移不把这次失败改成通过。

本次注册、开读、读回末采样的ordinary free分别为363,986,944 B、338,444,288 B、320,450,560 B。并行任务期间容量可变化；这里保留观测值，没有将其变化归因于某一未被证明的原因。

## 完整报告与身份

[完整独立读回报告](sandbox:/workspace/scratch/34f8fcac2ab1/r7-audit/storage-migration-followup-v1/R7_ARCHIVED_EXPANSION_MIGRATION_INDEPENDENT_READBACK_V1.json)：3,925,588 B，SHA256 `abce98e87fe1ebeab625647180904a42542dcc19d71f4b80b9f91b7f14fe5398`。

[预登记计划](sandbox:/workspace/scratch/34f8fcac2ab1/r7-audit/storage-migration-followup-v1/R7_ARCHIVED_EXPANSION_MIGRATION_INDEPENDENT_READ_PLAN_V1.json)：7,070 B，SHA256 `3d943f67526a2c223c4b35308b3452ce4aa8a66578a96cc1306417f3db957300`。

[只读源码](sandbox:/workspace/scratch/34f8fcac2ab1/r7-audit/storage-migration-followup-v1/read_archived_expansion_migration_r7_v1.py)：23,291 B，SHA256 `307990c1a8a9f33566911115d780c030317c8f27dc70a1fbfca6168e0b2c8cb8`。

所有原有限姿态结论保持其原范围；`all_blockers_closed=false`。
