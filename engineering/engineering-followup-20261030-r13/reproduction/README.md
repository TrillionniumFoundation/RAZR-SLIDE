# R13 执行输入定位与 R11 原报告补回

**补回后，60 条输入声明、52 个不同 size+SHA-256 身份均能在当前仓库的实际普通文件中定位。** 这里只验证内容身份和位置，没有重跑 CAD、算术或数值任务，也没有复现原环境或新增科学资格。

最新逐项映射见 [after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json](after-recovery/R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json)。首次快照及其说明原字节保留在 [first-snapshot/](first-snapshot/)。两次观察的 HEAD 都是 `ab9ef3270a9a0d0d28f605f7188038db133dbcd8`，分支为 `evidence/full-sprint-20261030-r13`。

| 快照 | 全部声明 | size+SHA 均匹配 | 该 HEAD 已含同字节 | 仅当前工作树/索引 | 仓库缺件 |
| --- | ---: | ---: | ---: | ---: | ---: |
| first-snapshot | 60 | 58 | 38 | 20 | 2 |
| after-recovery | 60 | **60** | 38 | 22 | **0** |

60 条包括 envelope INPUT_MANIFEST 的 14 条、geometry INPUT_MANIFEST 的 35 条，以及 geometry EXTERNAL_DEPENDENCIES 的 11 条。JSON 为每条列出原始绝对路径、原件字节数/SHA、包内副本、全部同字节的**仓库相对路径**及建议定位路径。精确工作树字节还与该 HEAD 的实际 git blob 比较，未把待提交文件误称为 HEAD 或远端已经包含。

## 新增的两份原报告

| 新仓库路径（相对本目录） | 字节 | SHA-256 |
| --- | ---: | --- |
| `recovered-r11-inputs/roi-producer-v2-report.json` | 91,568 | `6364eac059af54df2cc947bd75f6baa05a38fe4fb6c1f6951beed1d335dbf8c5` |
| `recovered-r11-inputs/roi-reader-v2-report.json` | 57,774 | `22d11a5538671d1f0709630814a25d29ef3fccf3533fb3998e5c9a11fd5a73a3` |

它们分别来自原 R11 `geometry-proof/roi-producer-v2/report.json` 与 `roi-reader-v2/report.json`，用于 R13 `build_current_structural_inputs.py` 的既有证据来源核对。复制前后均验证原件大小/SHA及逐字节一致；原路径和用途见 [RECOVERED_R11_INPUT_IDENTITIES.json](RECOVERED_R11_INPUT_IDENTITIES.json)。**这是补回原始输入，不是新的 R13 几何执行。** R12 和已封存的 R13 geometry/envelope 文件没有修改。

## 远端用户怎样定位

以最新 JSON 中的 `preferred_repository_path` 或 `repository_matches[].repository_path` 为仓库根下的相对路径，并验证同条的 `required_bytes` 与 `required_sha256`。不要仅凭文件名选择原件。常用前缀如下：

- R13 当前证据：`engineering/engineering-followup-20261030-r13/envelope/`、`engineering/engineering-followup-20261030-r13/geometry/inputs/`。
- R12 完整边界/旧正箱：`engineering/engineering-followup-20261030-r12/panel-filling/`。
- 旧 R11 whole KEY 的同字节 BREP：`engineering/engineering-followup-20261030-r12/geometry/inputs/`。
- 两份补回报告：本目录 `recovered-r11-inputs/`。

`exact_bytes_present_at_observed_HEAD` 描述上述 **ab9 HEAD**。22 条仅工作树/索引匹配包含 16 个 R13 STOP/SPRING BREP/STEP、四份 R13 trim 原件/账本以及两份新补回报告；它们应随 R13 发布后由用户对实际发布提交重新核验。本映射没有查询或保证最终远端状态。

## 内容齐备后仍需布局/路径适配

**60/60 内容齐备不等于原脚本可在任意 clone 中直接运行。** 原源码和报告中的绝对路径均保留，没有由本工具改写。

1. INPUT_MANIFEST 的 `source_path` 通常是冻结副本的来源。主执行程序读取包内 `inputs/`；但重新执行 input preparation 时，仍需恢复来源布局或另存路径适配版本。
2. `geometry/audit_r13_trim_independently.py` 原先依赖平级 `r13_envelope_work/` 和 `panel_fill_work/exterior-refinement-attempt1/`。仓库的 `envelope/`、`geometry/` 与 R12 `panel-filling/` 不自动满足该布局；负控保存脚本继承同样路径配置。
3. `geometry/build_current_structural_inputs.py` 原先使用固定 R11 根及 `roi-producer-v2/report.json`、`roi-reader-v2/report.json`、`roi-inputs-v1/*_KEY.brep`。本次补回报告采用上表文件名，**没有创建那棵原目录子树**。需依据映射在独立重放区恢复结构，或另存明确的逐文件路径适配代码。
4. `geometry/prepare_inputs.py` 还保留原 f11 仓库、R9 recovery 目录及 `geometry_work` 兄弟目录。复制到 R13 的 49 个冻结输入已经定位，来源路径本身没有因此变得可移植。

路径适配必须另留新执行身份，不应修改封存脚本后沿用旧执行 SHA。原解释器、native library、OCP/NumPy、平台行为及科学输出没有在本项任务中重现；记录一致性、native 材料语义和物理资格的既有边界均不改变。

## 留存与核验

成功映射源码为 `map_execution_inputs_v2.py`。它只枚举普通文件、按大小筛选 SHA、只读核对 git blob，并重新读取选定候选；不解包归档、不运行项目科学模块。首版 parse 错误的原源码和记录也保留，没有改写成成功。

`independent-review/` 另存独立复核源码与报告：它实际核对全部 60 条首选及全部列出的候选，逐条检查 11 个外依赖和两份补回原件，并用 `git cat-file` 读取 HEAD blob 再核对大小/SHA，确认 38 条 HEAD、22 条工作树匹配。此复核同样没有执行科学模块。

`REPRODUCTION_READBACK.json` 保存本次交付各文件的字节数和 SHA、两快照原字节核对以及两份补回原件身份。该回读自身由最终提交/交付清单绑定，避免自包含散列循环。后续仓库状态变化应另存映射快照，不覆盖本次历史观察。
