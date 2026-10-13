# RAZR SLIDE 当前资料盘点与版本归并

盘点时间：2026-10-13。仅检查 Library 元数据；没有修改或删除任何原文件，也没有把同名或同尺寸当作内容相同。

## 范围和数量

- 连续读取 5 页、每页 200 项，覆盖 2026-10-06 至 2026-10-13。项目资料首次出现于 2026-10-09。
- 名称明确指向 SLIDE / RAZR_SLIDE 或同期 R 编号的资料：**690 项**。
- 另保留 **38 项**图表、概念图或相邻辅助文件候选；其中通用 image-gen 名称仍需看图确认。
- 本盘点合计 **728 项，3,552,594,718 字节**（约 3.31 GiB）；这包括大量累积包，不能视为独立工程内容量。
- 文件类别：121 个 ZIP、205 个 JSON、157 个 Markdown、87 张 PNG、78 个 SHA-256 文件、29 个 PDF、25 个 HTML、18 个 CSV、3 个 GIF、2 个 STEP，以及各 1 个 Python / JSONL / LOG。
- 原始五页结果包含其他项目元数据，仅用于内部复核。可提交的是本目录的 `razr-slide-library-inventory.json`、CSV 和本报告，不能把原始 list-page 文件公开为项目资料。

## 最新候选与历史编号关系

**最新 CAD / FPC 包的元数据候选是 R44_FPC_full_verified_20261013.zip（北京时间 11:06:38），不是编号更大的 R79。**

R79 是另一条持续硬门槛增量资料的最新候选（北京时间 09:41:19）。元数据能确定文件时间、大小和身份，不能证明 R79 覆盖 R44 或 R44 覆盖所有旧分叉。工程基线必须再由 ZIP 的祖先哈希与文件成员关系确认。

| 家族候选 | 时间范围 | 保留方式 / 待确认关系 |
|---|---|---|
| SLIDE_R1 / R2 → R3A → R4 → R38 | 10 月 9 日至 11 日 | 早期形态、机械演进及原失败证据；不得按最新编号删除 |
| R39–R41 的 20261011 engineering_package 多份 | 10 月 11 日 | 同名编号有不同字节量，属于需要独立保留的分叉或重做包 |
| R41–R79 negative / incremental hardgate 家族 | 10 月 11 日至 13 日 | 连续的数学、路径、供应商资格和否决证据候选；R79 为最新增量 |
| R39_FPC_motion_20261012 → R40 → R41_FPC → R42_FPC → R43_FPC → R44_FPC | 10 月 12 日至 13 日 | 直接接续本次跨舱 FPC 三维 CAD 任务的当前候选家族 |
| R39_verified_engineering_package_20261013 | 10 月 13 日 10:10 北京时间 | 独立 R39 重算 / 复核包候选，晚于部分 R40–R42 文件，不能用时间替代祖先关系 |

## 应先读取 / 归档的当前条目

| 文件 | Library ID | 原始字节 |
|---|---|---:|
| R44_supplier_RFQ_20261013.md | `libfile_0763da3ac5d4819196252368c9c08504` | 2,073 |
| R44_results_20261013.json | `libfile_55ba7b9fd7a08191a652cc4cfd0266b2` | 1,976 |
| R44_hardgate_audit_20261013.md | `libfile_e5cc64b87f008191a0980220eae2f2d3` | 8,642 |
| RAZR_SLIDE_R44_FPC_delta_verified_20261013.zip | `libfile_e8c58863c094819184ec9e6ac111edbf` | 3,791,133 |
| RAZR_SLIDE_R44_FPC_full_verified_20261013.zip | `libfile_9d98b14a430c8191a85cc71916134c34` | 98,040,274 |
| RAZR_SLIDE_R39_verified_engineering_package_20261013.sha256 | `libfile_e89657138fb881919ef14b315750ae7a` | 123 |
| R39_hardgate_audit_20261013.md | `libfile_49f0f94dd1a08191859521ecf21a4dd0` | 7,376 |
| RAZR_SLIDE_R39_verified_engineering_package_20261013.zip | `libfile_877f6e2556008191b93e0c4ecfb1a255` | 85,173,281 |
| R79_hardgate_audit_20261013.md | `libfile_825019d0b8cc8191aa8885c87d16a94e` | 7,558 |
| RAZR_SLIDE_R79_verified_incremental_hardgate_20261013.zip | `libfile_e60bff7597ec8191a71dacb31b7cfd4d` | 51,780 |
| RAZR_SLIDE_R77_complete_offline_math_replay_20261013.zip | `libfile_7fd07d8949a081918c9178bc4615d577` | 330,380 |
| R44_results_20261011.json | `libfile_c61ee67aed188191b16866602ea660be` | 2,389 |
| R44_supplier_RFQ_and_product_decision_20261011.md | `libfile_c939e84c45308191af6af8cd43ce7a29` | 2,867 |
| R44_hardgate_audit_20261011.md | `libfile_f953c7cf42a08191b61606c9dd648df0` | 7,890 |

## 去重审计

仅按去掉 `(1)`、`(2)` 等名称后缀归并，找到 **56 组名称重复候选**。同尺寸重复仍未做 SHA-256，全部保留。

以下同名包尺寸不同，**不得合并或覆盖**：

| 同名基线 | 实际尺寸 / 身份 |
|---|---|
| R31 engineering_package 20261011 | 49,586,751 字节（libfile_4f30cfe2408c819180253fe61b1e9968）；46,989,185 字节（libfile_5d35b12a37c88191a060e82e87fc9d81） |
| R39 engineering_package 20261011 | 85,327,508 字节（libfile_9ff57f43d7e48191b13508a17d0d7b65）；81,131,498 字节（libfile_e5d5fadb135481919de4886efe515b4c）；80,644,784 字节（libfile_47de3a068ac08191b121d15c14d83313） |
| R40 engineering_package 20261011 | 90,933,739 字节（libfile_6c8c6e61a4548191aeb96aab47371026）；81,536,117 字节（libfile_bc9da07ff6408191ae8474928c516863） |
| R41 engineering_package 20261011 | 85,595,500 字节（libfile_bb39e0af6d8c8191806220a1f58040ae）；87,268,038 字节（libfile_af80f98ba0b8819190e9d1b40c3a539f） |

相关 R31 / R39 / R40 / R41 的审计、JSON 和 RFQ 文档也有不同字节量，需同样保留。细目见 inventory JSON 的 `duplicates` 字段。

## 资料完整性的边界

- 有项目 / 版本名称的资料已按本次五页窗口全部保留在清单中。尚未证明通用名概念图的归属，未证明完整 ZIP 对所有单独导出文件的包含关系。
- 同尺寸只是候选重复，不是哈希证据。历史累积包与最新完整包之间仍须逐成员核对，才能选择实际字节归档策略。
- 本次 inventory 不是机械、电气、OLED 或整机制造资格；不能改变 `manufacturing_go=false`。

