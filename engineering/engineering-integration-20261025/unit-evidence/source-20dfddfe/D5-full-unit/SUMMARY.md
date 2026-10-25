# S3 / D5 完整单元执行：1653 通过，1 条生成入口同步断言失败

这是 **derived_public_summary**：只公开审核过的汇总、来源身份和原件哈希。完整原 ZIP 与私有完整证据已保存且保持原字节；此目录不含原始 API、job 日志、邮箱、进程或环境明细，也不提供私有文件定位信息。

## 实际来源与结论

功能源 **S3 20dfddfe8497a73b1814623e6320b3a9ac4273d0**；工作流提交 **b76ea33b9cc892e46698755a0b4be64da3ce0468**。[实际 run 40208304041](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40208304041)，attempt 1，unit job 121213901253。

原 `tools/verify.py` 确实完成 **36 套 / 1654 个测试**，原 exit **1**：**1653 pass / 1 failure / 0 errors / 0 skipped**。35 套通过，product-integration 套的 196 个测试中有 1 条失败。13 个新增测试已实际通过，不能替代完整源资格。

唯一失败是 `test_product_state.ProductStateTests.test_generated_entrypoints_are_current`。原日志在 `docs/RESEARCH_OVERVIEW.md` 比较到配置总数仍为 **1641**，而 S3 manifest 要求 **1654**。这是原单元测试真实 assertion failure，不是安装、源身份、环境、时限或后验包装失败。该测试在首个不一致文件处中断，因此原失败本身不能证明其他生成入口已同步。

源码与 43 锁包前后身份、完整 suite 顺序均核验通过；外层时间 cap 未触发。原结果保持 S3 身份，不改写为 C2 或后续 S4。C2 候选仍保留，S3 不因三组几何执行成功而取得完整单元资格。后续 S4 生成入口修复必须通过自己的完整 36/1654 执行，本摘要不预报其结论。

## 原件与范围

原 ZIP **S3-D5-full-unit-40208304041-1.zip**，**2,289,211 B**，SHA256 **0ad2c037da2791ba3f01c47196c34f858e10906555966201128030a17e3af26f**。741 个成员 / 740 个 manifest 内容与全部 36 原日志、JSON 的 ID 顺序已由两位读者分别核验。裸 test ID 跨套有 14 个合法重复；实际计数以 suite + test 身份为准。

平台外层 30 分钟作业窗口与 1620 秒 cap、原各套超时均保留；没有因此放宽原测试断言。实际资源范围是 service 及后代，不能等同整 VM。此完整单元执行不证明完整连续运动、结构/公差、G2、实物或制造资格。

`OUTCOME.json` 提供审核过的聚合结果；`ARCHIVE_REFERENCE.json` 只给文件名、大小、哈希、源码和公开 run URL。其余文件为派生清单与敏感内容检查。完整原件保存在授权私有目的地，原始失败未被删除或改写。
