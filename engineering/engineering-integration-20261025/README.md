# 2026-10-25 全量执行：统一候选与工程闭环

工作入口：[PR #39](https://github.com/TrillionniumFoundation/RAZR-SLIDE/pull/39)，分支 `work/engineering-integration-20261025`。

本次按软件集成、完整实体运动、原数值模型、真实器件和实物验收五条线执行。完成与否以实际原始回执和输入身份为准；配置中的测试数量、准备好的程序以及空白实物模板均不计作完成的验证。

## 版本身份

统一祖先 `363113ffe887b5d09a03b82fdbe948ae92a7f572` 同时包含 PR36 → PR37 → PR38、资格修复 `a9aaf481b1e51caa948f824aa4768af1f5b3d57a` 和主线 `92d80fbef80bef4cde8dc7d759399f19fe8ba7ce`。主线删除根 README 的决定被保留；自动生成入口改为 `docs/RESEARCH_OVERVIEW.md`，并与 `CURRENT_DESIGN.md`、`status.json` 同源。

PR35 `176df31ceb35bb3737d68030e60ba377665de210` 保持独立的归一化 bearing 研究模型身份。其旧正、负证据和本次原 K/C 重建诊断均不构成当前 EP5 壳体结构资格。

最终功能候选在源码冻结后以 `candidate/engineering-integration-20261025` 固定。完整测试回执必须记录其实际执行 SHA。随后追加的原始回执和报告有独立提交身份，不得把它们改称已经测试过的功能源码。

首个候选 `8fa8ae2bae5de8808ad8259e04434bdd18d47541` 的完整验证尝试已中止并保留原始记录：本地稀疏检出遗漏了受控原生输入；SLIDE 独立启动还发现同名辅助模块的导入顺序错误，源码身份保护在启动 CAD 前正确拒绝。修复仅改变加载顺序并增加两个独立进程回归，不改变几何算法、材料或原资源门槛。该次尝试不是 36 套通过证据，详见 [原始回执](unit-evidence/first-candidate-aborted/RECEIPT.json)。新候选必须重新运行全部 36 套。

## 当前执行材料

| 工作 | 已实际完成的范围 | 仍需满足的条件 |
|---|---|---|
| 统一版本 | 完整祖先整合；入口迁移；43 个锁包版本一致；新增 77 项合同、ECAD 和独立进程入口反例回归 | 固定候选后的 36 套完整执行及原始回执；配置的 1,641 项不能先标为通过 |
| KEY 原实体 | 半带 STOW 的 154 个完整 body、11,781 对全部执行；两侧各两对真实碰撞与 Common STEP 身份恢复；独立原生 STEP 回读 | 完整正交集；有限修复候选的独立验证；实际机构允许域、强度和公差资格 |
| SLIDE / SEATING | r3 便携后继保留原算法、材料和资源守卫；原 65 / 50 项准备合同实际运行 | 新候选的原生逐对执行；非零偏移、独立伸缩分配和正反程全合法动作域 |
| 原数值模型 | panel 的 K 与 C 精确重现原字节；定位第 0 探针；保留三轮全部五探针、RHS、初始/最终全场及逐步修正指标 | 原 float64 `1e-7` 判据仍拒绝；不能接受 panel H 或继续原 checkpoint restore |
| 同版电气 | 独立 188 mm / 164 mm 自由段 EP5 连通图稿；26 路、52 pad、130 track 的实际解析检查；新增原生 KiCad CI 门禁 | 实际原生回执；OEM 端子分配、供应商叠层、阻抗/电流和动态资格 |
| G3 / G4 / G5 合同 | 当前 EP5 绑定；功能 × 17 阶段 × 原供电模式；寿命原始采样重算与连续 cycle 校验；缺测与失败分开 | 同一 specimen 的实物、来源明确的阈值、校准、预登记和实际顺序采集 |
| 当前 EP5 结构 | 从本次实际 native scene 提取 154-body 名义体积、边界和来源；独立材料/载荷/支承/公差输入合同 | 真实材料和载荷缺失，尚未建立完整当前 FE 网格，也未给出结构通过结论 |

具体记录：

- [机器状态](SUMMARY.json)、[实际运行环境](EXECUTION_ENVIRONMENT.json)。
- [几何原始与移植身份](geometry/PORTING.json)，以及 `geometry/evidence/` 中的执行材料。
- [数值结论](numerics/SUMMARY.json)、[数值方法与运行说明](numerics/README.md)、[原始探针包](numerics/RAW_EVIDENCE_PERSISTENCE.json)。
- [产品实现与复现](product/README.md)、[新增公开 OLED 来源核对](product/OLED_SOURCE_RECHECK.json)。
- [当前结构输入合同](structural/CURRENT_EP5_INPUT_CONTRACT.json)、[实际 STOW 实体清单](structural/nominal-STOW-body-inventory.json)。

## 必须保留的工程结论

原 KEY 的实际半带碰撞发生在 `L_CAP_0 × L_KEY`、`L_KEY × L_ROOT_INNER` 及其右侧对应体。体积分别约为 `0.001238206264` 与 `0.001650941685 mm³`，超过原 `1e-7 mm³` 门槛。原失败保留。有限端面回切是另一个明确命名的研究候选；在完成材料守恒、完整实体配对和域验证之前不改生产默认值，后续仍需要当前结构与工艺资格。

panel 第 0 个全 1 方向探针的原始相对残差约 `2.3849e-7`；其余四个通过。原 float64 修正、高精度残差修正以及保持 K/b/约束不变的对称均衡对照均没有让五个原检查全部通过。高精度残差更小不能替代原检查器。原始和最终全场已保留；中间迭代保留了残差、最差 DOF、修正范数及 iterate SHA，未保存每一步完整全场数组。

当前环境的历史 ADB 端口不可达且没有 adb 程序。本次没有新增实物测量、器件标签、实际端子或带电测试。十个未知 donor 身份字段、七类实物零件和十二类物理接口不得由公开商品页、名义空间占位或软件单测补写。公开 OLED 的额外筛选也未产生可冻结的当前屏幕 PN / revision / 动态叠层合同。

## 复现与验收次序

在实际功能候选 SHA 上运行：

```bash
uv sync --locked --no-cache
uv run --locked python -B tools/check_environment.py
uv run --locked python -B tools/verify.py --expected-head <candidate-SHA> --output <new-output>
python3 tools/sync_current_design.py --check
```

本次受限本地环境使用原锁中的 22 个带哈希安装包叠加 21 个版本已精确一致的包；43 版本检查完整通过，未声称重新证明已有 21 个 wheel 的安装来源。原生 KiCad job 独立固定官方 PPA 的 `9.0.9~ubuntu24.04.1` 构建及其 `.deb` SHA256；Ubuntu 默认的 KiCad 7 不提供所需 CLI DRC。KiCad 9 后继回读器明确选择原生封装写入器，保留旧回读器原字节。实际运行完整保留原生读取和 DRC 的所有级别结果，不能用解析器检查代替。

实物按 G3 无电装配/动作 → G4 带电功能与动作 → G5 寿命/环境/工艺执行。模板中的载荷、操作力、偏斜、采样、同步、温度、循环和失效阈值必须填入真实来源后才能冻结；没有用新数字填补未知值。

`candidate_go`、`fixture_fabrication_go`、`manufacturing_go` 继续为 false。
