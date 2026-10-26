# 2026-10-25 全量执行：候选、实际结果与下一步

S4 功能候选已在同一源码版本完成 **36 套、1,654 项实际测试**，两层 KEY 让位研究件的两个有限位置也分别完成 11,781 对全新配对及独立 STEP 读回，均无正 Common；未修改结构的对照保留原四处真实交叠。原版 KEY v4 六组、严格恢复读回及独立正交点已完成。L1 的 89 次精确重放补齐了异常和中间材料，并确认 A_BACK_PANEL 与左右 KEY 在声明名义刚体 pair 域内有四个有限姿态正 Common 见证。完整 SLIDE、全数值求解、真实器件及 G3/G4/G5 实物资格仍未闭合。

- [完整执行报告](EXECUTION_REPORT.md)：结果、失败原因、证据范围与限制。
- [下一步工作计划](WORK_PLAN.md)：用户十个工作包的现状、职责、依赖和验收条件。
- [证据索引](COMPLETED_EVIDENCE_INDEX.json)、[机器状态](SUMMARY.json)、[同一实物现场交接单](product/PHYSICAL_HANDOFF.md)。
- [草稿 PR #39](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/39)，工作分支 `work/engineering-integration-20261025`。

## 版本身份

当前已通过同版完整软件验证和指定有限几何验证的功能候选为 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`（S4），候选引用为 `candidate/engineering-integration-20261025`。它继承 C2 `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb` 已整合的 PR36 → PR37 → PR38、资格修复 `a9aaf481b1e51caa948f824aa4768af1f5b3d57a` 和主线 `92d80fbef80bef4cde8dc7d759399f19fe8ba7ce`。主线删除根 README 的决定被保留；`docs/RESEARCH_OVERVIEW.md`、`CURRENT_DESIGN.md` 与 `status.json` 均由 `design/current_product.json` 生成。

证据、报告和台账后继提交不自动继承“本提交完整测试通过”的身份。C2、S3、S4 的原始运行 SHA、每次实际源码/输入字节、工作流提交与证据提交分别记录，详见 [候选身份](CANDIDATE_IDENTITY.json)。

S3 `20dfddfe8497a73b1814623e6320b3a9ac4273d0` 增加显式两层 KEY 让位研究选项、完整材料读回及两个 SLIDE reader 的最小导入修复。其 [D5 运行](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40208304041) 三个几何作业完成，同版软件验证因生成文档仍声明 1,641 而失败，原失败完整保留。S4 由原生成器同步三个入口文档后，在 [D6](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40210734348) 重新实际完成全部 36 套 / 1,654 项及三个完整有限几何作业，并经过独立复核。D5 原件没有改标成 S4。

PR35 `176df31ceb35bb3737d68030e60ba377665de210` 继续是独立的归一化 bearing 研究模型。20261023 的受控 K/C 重建与本次数值诊断不等同于最早 historical-volume-v3 原 K，也不构成当前 EP5 壳体结构资格。三份设计配置保留的 `a1b3cc1e…` 是历史共同实现基线；当前同版验证源码是 S4，不能只修改一份配置的基线标签来伪造新身份。

首个候选 C1 `8fa8ae2bae5de8808ad8259e04434bdd18d47541` 的中止尝试保留在 [原始回执](unit-evidence/first-candidate-aborted/RECEIPT.json)。修复稀疏输入缺失及 SLIDE worker 导入顺序后，全部 36 套已在 C2 重新实际执行。

## 已执行结果

| 项目 | 实际结果 | 结论范围 |
| --- | --- | --- |
| S4 / D6 完整软件验证 | 36 套 / 1,654 项全部实际通过；43 个锁包版本、Python 3.12.14 和 uv 0.10.10 一致 | 1,654 个唯一 `(suite, test_id)`，裸 test ID 为 1,640；原报告和全部 suite 日志已独立核验。不是物理资格 |
| C2、S3 软件历史 | C2 原 36 套 / 1,641 项通过；S3/D5 的同版验证因生成文档计数未同步而失败 | 两次原身份、原成功及失败都保留；S4 的新通过不覆盖历史回执 |
| 固定控制姿态 | C2 STOW 154 bodies / 11,781 clear；OPEN 161 / 12,880 clear | 两个固定姿态，新 C2 PREDOCK 未执行；不外推完整运动 |
| 原版 KEY v4 / D4 | 六组均实际执行并通过证据验证；STOW HALF/FULL 各保留四个阳性，其余四组 finite clear；原严格 resume 六组只读回、零 native 补算 | 20,880 fresh + 53,103 同源固定对复用；四个 pair 在两个位置形成八次阳性记录。六组原 profile 域外拒绝均保留，不是完整 factory 或连续域资格 |
| C2 独立正交点 / D4 | `candidate=none`、STOW `dx=+cam, dq=cam-yoke`，11,781 全 fresh、零阳性/求值错误，独立 reader 通过 | 一个有限槽顶点，不等于完整正交组合或独立手动域 |
| SLIDE r3 / L1 | 原 11,781 条分类保留：11,762 clear / 10 enclosure unresolved / 9 evaluation failure；L1 的 E17/O72 共 89 次实际返回与原件完全相同 | 新增 505 个逐 case 材料记录、1,010 个 STEP/BREP 导出；25 个真实 ValueError 与 272 个正常 GeneratorExit 分开。四个 A_BACK_PANEL/KEY 名义刚体有限姿态有整件正 Common 见证；其余 height/spring 包络不升级为碰撞。完整 SLIDE 仍未通过 |
| SEATING r3 | 11,781 external pairs 全 clear，独立 reader exit 0 | KEY/crosshead=0、左右独立伸缩分配的原声明外部配对域；不证明连续柔性自有效性或整个 G2 |
| KEY 原单层让位研究件 | C2 FULL_BAND 重算 11,781 对，仍有左右 KEY×ROOT_INNER 两处各约 0.00649356 mm³ 交集 | 原负证据保留；材料守恒与独立 STEP 读回通过不等于几何通过 |
| KEY 两层让位研究件 / S4 D6 | FULL_BAND、ORTHOGONAL 各 154 体 / 11,781 全 fresh，均零 Common/求值错误、独立 reader 通过；新 `none` FULL_BAND 对照仍为原四处阳性 | 三作业共 35,343 新配对 / 70,686 journal 事件；四改体仍各一个有效正 solid，14 个 cut-box 和双向重建通过。S3/D5 的先前运行另存；两个负 dq 点不外推正 dq STOP/SPRING factory 域、连续运动、强度或容差 |
| panel / frame | 三种 panel 有界策略均 4/5；probe 0 原 float64 残差仍超过 1e-7。frame 5/6 GiB 分解均资源失败，0 RHS 求解 | 未取得完整 H、trace/restore 或接触资格；原失败与各运行源码身份均保留 |
| hosted panel N1 / N2 / N3 | N1 COLAMD / AS 6 GiB、N2 MMD_AT_PLUS_A / AS 6 GiB 均在因子扩容阶段失败；N3 显式 AS 8 GiB 在原 180 秒墙钟到达后终止 | 三次均为五 RHS 已准备、零 solve/field/residual。N3 没有同句 malloc 错误，不能把 AS 认定为唯一原因；原残差门槛 1e-7 与 shared 6.8 GiB 不变 |
| EP5 188 mm ECAD | 实际 KiCad 9.0.9 原生回读及全 severity DRC：0 项；52 terminals / 130 tracks / 0 unconnected | 26 路自有导通研究网；未执行原理图 ERC，不提供 OEM pinmap、功率、高速或动态资格 |
| G3/G4/G5 合同与当前结构输入 | 同候选门控、原始采样重算、unknown/fail 区分及 154-body / 13 类载荷输入合同已实现 | 真材料、真实阈值、实际端子和同 specimen 原件仍缺；没有新的 G3/G4/G5 实物结果 |

工程聚合、原始包 SHA256 和独立复核摘要见 [证据索引](COMPLETED_EVIDENCE_INDEX.json)。[D5](geometry/evidence/source-20dfddfe/D5-finite/SUMMARY.md)、[D6](geometry/evidence/source-dd7def6e/D6-finite/SUMMARY.md) 和 [L1](geometry/evidence/candidate-bec1c8d7/slide-L1/SUMMARY.md) 公版均为明确标注的衍生聚合；完整原 ZIP、材料、运行日志/API 与进程环境记录另行私有保留，未复制进这些公版文件。hosted 的失败、接口探针与原生执行分别归档；短探针成功不能代替 CAD 或未来资源资格。

## 复现边界

复现当前同版软件验证时，在独立的 S4 checkout 中使用锁环境，并为每次执行创建新输出目录：

```bash
uv sync --locked --no-cache
uv run --locked python -B tools/check_environment.py
uv run --locked python -B tools/verify.py --expected-head dd7def6e6a4de9f47dc91ca2ab336fb1a8828560 --output /path/to/new-output
python3 tools/sync_current_design.py --check
```

复现须读取对应原始包内的命令、路径绑定与资源记录。C2 的原 r3、v4 和 L1 证据仍绑定 C2；D5 绑定 S3，D6 绑定 S4。证据后继 HEAD 不能只填旧标签。G3/G4/G5 的严格当前候选检查同样适用；新增功能修改需新候选、新的相关验证和重新冻结的实物计划。

本地 43 个包版本检查实际通过。另对 21 个预存包取得原锁 wheel，核对 1,650 个包 payload 文件和 86 个原 metadata 文件，未发现差异；这支持磁盘字节身份，不追溯证明原安装过程或当时每个内存执行字节。[完整环境证据](environment/locked-wheel-payloads-bec1c8d7/SUMMARY.md)

## 当前实物依赖

当前可见环境没有 adb，历史 ADB 端口实际连接被拒绝。本轮没有新增 donor 标签、三维实测、真实端子、实物装配或带电测试。十个未知身份字段、七类实件和十二类接口须来自同一 specimen 原件；四个名义空间占位尚未替换为实测包络。

现场次序为：同 specimen 身份/器件/接口基线 → OLED/FPC 和当前结构/电气输入冻结 → 有来源的 G3/G4/G5 计划 → G3 无电装配与动作 → G4 带电功能与动作 → G5 寿命、环境与工艺。具体采集字段、校准和职责见 [现场交接单](product/PHYSICAL_HANDOFF.md)。

`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 均继续为 **false**。

Current physical collection templates are in [the S4-bound empty packet](product/qualification-s4/README.md): four unchanged original templates, zero new measurements, G4/G5 unknown, all physical/release flags false. The C2 packet keeps its historical identity.
