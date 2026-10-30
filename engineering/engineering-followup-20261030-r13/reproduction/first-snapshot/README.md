# R13 原执行输入 → 仓库文件内容定位

本目录只回答“原执行输入的字节在哪里”。完整逐项映射见 `R13_EXECUTION_INPUT_TO_REPOSITORY_MAP.json`：60 条声明、52 个不同的 size+SHA-256 身份，覆盖 envelope INPUT_MANIFEST、geometry INPUT_MANIFEST 和 geometry EXTERNAL_DEPENDENCIES 的每一条记录。

本快照观察的分支为 `evidence/full-sprint-20261030-r13`，HEAD 为 `ab9ef3270a9a0d0d28f605f7188038db133dbcd8`。扫描实际仓库普通文件，先按大小筛选，再计算 SHA-256；没有把同名文件、归档成员名或 git LFS 指针当作原件。精确工作树字节的 git blob 身份另与该 HEAD 比较，避免把尚未提交的 R13 文件误写成该提交已经包含。

| 声明来源 | 总条数 | 该 HEAD 已有同字节文件 | 仅当前工作树/索引找到 | 仓库无同字节普通文件 |
| --- | ---: | ---: | ---: | ---: |
| envelope INPUT_MANIFEST | 14 | 14 | 0 | 0 |
| geometry INPUT_MANIFEST | 35 | 19 | 16 | 0 |
| geometry EXTERNAL_DEPENDENCIES | 11 | 5 | 4 | 2 |
| **合计** | **60** | **38** | **20** | **2** |

全部 60 个原始绝对路径在制作此快照的本地环境仍存在，且大小与 SHA 均匹配声明。远端用户不能据此假定这些 `/workspace/scratch/...` 路径也存在。

## 如何读 JSON

每条记录保留原 manifest、原始绝对路径、所需大小/SHA、包内副本位置，以及全部匹配的**仓库相对路径**。`preferred_repository_path` 只是定位建议；每个候选都须同时匹配大小及完整 SHA。`exact_bytes_present_at_observed_HEAD` 区分该 HEAD 的实际 blob 与当前工作树中的新增文件。

通常可优先定位以下路径前缀（均相对仓库根）：

- R13 envelope：`engineering/engineering-followup-20261030-r13/envelope/`。
- R13 geometry 冻结输入：`engineering/engineering-followup-20261030-r13/geometry/inputs/`。
- R12 完整 panel/KEY 边界与原正箱：`engineering/engineering-followup-20261030-r12/panel-filling/`。
- R12 whole KEY BREP：`engineering/engineering-followup-20261030-r12/geometry/inputs/`。
- 原构造/运动源码及 R9 合同：JSON 同时列出当前 `integration/`、R9 或其他逐字节相同位置。

仅工作树/索引找到的 20 条是 R13 的 16 个 STOP/SPRING BREP/STEP 输入，以及四份 R13 trim 原件/账本依赖。该观察不声称它们已存在于上述 HEAD 或任何远端提交；发布后应以实际发布提交重新检查。

## 本快照未在仓库找到的两个输入

| 原输入（相对原 R11 geometry-proof 根） | 大小 | SHA-256 |
| --- | ---: | --- |
| `roi-producer-v2/report.json` | 91,568 B | `6364eac059af54df2cc947bd75f6baa05a38fe4fb6c1f6951beed1d335dbf8c5` |
| `roi-reader-v2/report.json` | 57,774 B | `22d11a5538671d1f0709630814a25d29ef3fccf3533fb3998e5c9a11fd5a73a3` |

两者原始根为 `/workspace/scratch/f11ac2a81fe4/RAZR-SLIDE/engineering/engineering-followup-20261030-r11/geometry-proof/`。本地原件存在且身份匹配；本工具没有将其复制进仓库，也没有把仓库外的文件可用性当成远端可用性。对应 R11 `roi-inputs-v1/L_KEY.brep` 和 `R_KEY.brep` 的同字节文件则已经能在 R12 geometry inputs 中定位。

## 仍然需要处理的路径/布局

**内容匹配不等于可直接复现原环境。** 这些映射没有创建原目录布局，也没有修改封存脚本。

1. 两份 INPUT_MANIFEST 的 `source_path` 是冻结副本的原始来源。主程序读取包内 `inputs/`，不必仅因来源字段是绝对路径就重建所有旧路径；但若重新执行最初的 input preparation，仍须按映射恢复来源布局或另存明确的路径适配版本。
2. `geometry/audit_r13_trim_independently.py` 原来使用 `HERE.parent/r13_envelope_work` 与 `HERE.parent/panel_fill_work/exterior-refinement-attempt1`。仓库的 `envelope/`、`geometry/`、R12 `panel-filling/` 名称并不自动满足这些兄弟目录约定；负控保存脚本也依赖该 checker 的路径配置。
3. `geometry/build_current_structural_inputs.py` 和原 sealing 路径记录使用上述固定 R11 绝对根。其中两个报告在本快照缺于仓库；只有 KEY BREP 的内容匹配不足以替代报告。
4. `geometry/prepare_inputs.py` 还记录原 f11 仓库、R9 recovery 原件目录和 `geometry_work` 兄弟目录。49 个冻结输入副本已逐项找到，但这些准备阶段的原绝对路径并未因复制副本而改写。

应保留原封存源码及执行散列；任何路径适配应另存并记录映射及新执行身份。本工具没有核验原解释器、OCP/NumPy/native library、平台舍入或依赖安装，也没有执行 CAD、算术证书、数值求解、几何或物理资格复验。

## 映射工具与留存

成功执行源码为 `map_execution_inputs_v2.py`，仅运行文件清单、大小/SHA、git 只读身份和选定文件的再次字节核验。它扫描了 2,708 个普通文件，对 89 个大小候选计算散列，并再次读取 51 个选定仓库路径。首版解析错误及原源码保留在 `MAPPING_ATTEMPT_1_FAILURE.json` 和 `map_execution_inputs.py`；该失败发生在 Python parse 阶段，没有开始任何输入或科学执行。

若仓库后来补入缺件或提交发生变化，应另存新的输出快照；本 JSON 的 HEAD、时间和缺件状态描述的是这次观察，不自动跟随未来仓库状态变化。
