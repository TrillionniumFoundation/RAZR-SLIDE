# 产品集成验证：原始失败、修复运行与不重复的套件选择

本次保留了初次失败的完整证据，并完成限定范围的修复验证。正式汇总采用两个执行中互不重复的套件集合，覆盖 **32 组、1240 项**；**`single_full_run_passed=false`**。这表示现有覆盖来自两次带有各自源码和环境身份的执行，不能改写成某一次整仓运行全部通过。

## 1. 实际执行结果

| 执行或选择 | 源码身份 | 套件数 | 实际测试数 | 结果及用途 |
|---|---|---:|---:|---|
| 初次 canonical 运行 | `b6abcb6`，完整身份见原报告 | 32 | 1220 | **FAILED**；配置要求1240项，实际少于配置数量，原始失败不改写 |
| 从初次运行保留的通过套件 | 同一初次执行 | 25 | 1058 | 全部通过，作为正式选择的第一部分 |
| 修复后的限定运行 | `3eae4e7258814c7f5454937535d6c642dd51662f` | 7 | 182 | **全部 PASS**，覆盖初次未通过的7组，作为正式选择的第二部分 |
| 不相交套件选择的合计 | 上述两个执行，各自保留身份 | 32 | 1240 | `25+7=32`、`1058+182=1240`；不是新的单次执行 |

初次运行的配置数量和实际执行数量分开记录；缺失依赖或输入导致部分用例未能正常执行，不计成已通过。修复后的182项也不能直接加到初次1220项上当作当前测试总数，后者包含需要被修复结果替代的套件。

[canonical-selection.json](canonical-selection.json) 列出所选择的套件及对应执行来源。选择要求两个套件集合无交集、并集覆盖配置的32组，并逐组保留实际结果与测试数量。由此得到1240项的覆盖汇总，同时保留 `single_full_run_passed=false`。本文件不将跨版本选择描述为一个新的完整运行回执。

## 2. 修复内容与断言边界

初次未通过的7组涉及五项冻结输入 SHA 登记、一项 `ezdxf` 导入问题，以及一项缺失的几何否定控制输入。修复补齐的是正确输入和可执行环境，原断言的实质要求继续保留。

| 问题 | 修复与保留的检查 |
|---|---|
| 五项冻结输入 SHA 登记不一致 | 恢复正确冻结输入与登记的一致性，继续执行逐项 SHA 校验；不删除固定输入检查，也不接受任意变更字节 |
| `ezdxf` 无法导入 | 使用隔离依赖副本，核查实际 Python/导入环境；按安装元数据 `RECORD` 完成 **397 个文件的校验**，结果见运行副本回执 |
| 缺失的历史几何否定控制 | 旧 `geometry-trial-r1` 原件没有被虚构为已恢复；从当前配置派生一个明确命名的新22 mm宽B电池反例，保留实际原生正交集断言和当前候选对照 |

新的 [geometry-wide-B-negative-control.json](../mechanical/geometry-wide-B-negative-control.json) 只把 `B_BATTERY_ALLOCATION` 的 X 下界从21改为11 mm，上界仍为33 mm，其他参数保持当前配置。测试在滑动40 mm的真实场景中要求宽反例与伸缩件具有大于 `1e-7 mm³` 的原生正交集，并用同一阈值检查当前12 mm分配。修复没有删掉否定用例、放宽交叠容差、跳过旧约束，或用 AABB 相交代替原生实体计算。它是可追溯的新否定控制，不具有旧 r1 的原始文件身份。

397个 `RECORD` 文件校验用于核实依赖副本内容与其安装登记的关系，既不是新增397项产品测试，也不是手机或材料的物理资格。实际环境和校验结果见 [runtime-copy-recheck-20261019.json](runtime-copy-recheck-20261019.json)。

## 3. 原始报告、日志及文件保存关系

| 文件 | 含义 |
|---|---|
| [initial-b6abcb6-report.json.gz](initial-b6abcb6-report.json.gz) | 初次32组、实际1220项、FAILED的完整原始报告 |
| [initial-b6abcb6-logs.tar.gz](initial-b6abcb6-logs.tar.gz) | 初次执行日志，保留具体失败和未完成原因 |
| [initial-run-summary.json](initial-run-summary.json) | 初次执行的简要结果与原始证据引用 |
| [repair-3eae4e7-report.json.gz](repair-3eae4e7-report.json.gz) | 修复后7组、182项全部PASS的完整报告 |
| [repair-3eae4e7-logs.tar.gz](repair-3eae4e7-logs.tar.gz) | 修复执行日志，与初次日志分开保存 |
| [repair-run-summary.json](repair-run-summary.json) | 修复执行的简要结果、源码与范围 |
| [canonical-selection.json](canonical-selection.json) | 25组1058项与7组182项的不相交选择及32组1240项汇总 |
| [artifact-preservation.json](artifact-preservation.json) | 保留下来的原件、丢失的旧文件和重新生成文件之间的身份边界 |
| [runtime-copy-recheck-20261019.json](runtime-copy-recheck-20261019.json) | 隔离运行副本、依赖导入和397个 `ezdxf` RECORD 文件校验 |

初次失败报告与日志作为原始证据保存，修复后的通过不会覆盖它们。2026-10-18 部分本地原生 CAD/FPC 报告、旧否定配置及归档在临时环境重置后丢失；旧哈希本身不证明旧字节仍可读取。2026-10-19 的原生重建使用新的执行记录、重新读回结果和新文件哈希，不冒用丢失输出的旧身份。

## 4. 原生几何、电气与实物的独立范围

机械重建的三份归档已封存并完成独立读回：STOW和PREDOCK各99个单体，OPEN为106个单体。另有14项针对性 CAD 测试、31个新增材料区域的9021次非自身比较及各项读回证据；这些保持自己的执行身份，**不能再把14项加到1240项总数中**。详见 [机械说明](../mechanical/README.md)。

FPC重建完成49个运动状态与15个手动操作状态，合计64条记录，全部拒绝且原生Boolean计算异常为0。运动部分有25个唯一材料几何姿态；64条记录不是64个唯一姿态，也不是64项单元测试。三个完整FPC/双端端接STEP各41个正体，独立台架夹具为8个正体。电气索引列90个文件，加索引自身共91个文件；见 [电气说明](../electrical/README.md)、[运动报告](../electrical/motion/motion-report.json) 和 [文件索引](../electrical/artifact-index.json)。

三份新生成的 PCB 源与已保留 KiCad v4 输入完全相同，继续引用该 v4 的零DRC、零未连接及零封装库错误结果；本次重建没有再执行KiCad。上述研究电路和几何检查均不能证明真实donor已装入或手机已接通。

最新donor只读采集在2026-10-19T01:19:54Z返回码2、`selected_donor_connected=false`。设备与实体模块没有因此被识别，实际针序、尺寸、供电、显示/触控、USB动态连续性和机械寿命仍待实物验证。交付状态继续保持 `candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false` 和 `physical_phone_verified=false`；各项实际执行身份统一索引于 [DELIVERY_VERIFICATION.json](../DELIVERY_VERIFICATION.json)。
