# RAZR SLIDE R79｜从 R78 鲁棒标量收放率到静止起停加速度硬门槛

**最终决策：`candidate_go=false`、`CAD_modify_go=false`、`manufacturing_go=false`。**

这份小型增量包不是 R39 原来的三维排线，也不是新 OEM CAD、带导线 FPC、USB 或电机控制固件。它建立在经外部 SHA256/CRC 校验的 **R78 数学父包**上；R77/R76 另作可核验数学祖先，不把 R41/R42 的独立 OCC 负面空间支系混入同一 CAD 祖先链。

- 保持两个最终同外形功能舱、单块约 7 英寸 OLED、B 上滑 79.75mm + 终点法向 8.2mm、A 优先电池、无独立外屏。4700mAh 仅目标；缺真实 OEM 等尺寸壳体和电芯数据。
- 固定原 R78 假设：总线长 **70mm**、必要动态弯曲半径 **R15mm**、端距误差 **E=±0.05mm**、投影端距 `(Y,Z)=(55,9.45)mm`、提前安全进入短弧模式。
- 新增**假设**：储线机构从静止起步与在 Y 滑程末端停止；在机械行程坐标 `s` 而非秒上设速率 `|F′(s)|≤K` 和有界加速度 `|F″(s)|≤A`。
- 新证明：在此标量必要区间模型内，只要终点收线速率为 0，**任何 K 都不能弥补 `A<0.187983876081... mm/mm²`**；有限 A 且起点静止时无法在 R78 的原 `K*=0.927702168571877...` 速率达到最优。
- 条件性、**非最优**存在性示例：`A=0.30, K=0.98`，在 806 个节点上解线性约束得到 C¹ 分段二次 F(s)，并用每段解析导数界证明整段不穿出 R78 窗口；最小保守余量只有约 0.0035mm。**没有真实电机、线材或 CAD 安装**。

## 独立复现

需要安装 Python、numpy、scipy、mpmath 并由你以只读身份提供 *外部* 原始 R78/R77/R76 ZIP；它们**没有包含在本增量包内**。

```bash
export R78_PARENT_ZIP=/path/to/RAZR_SLIDE_R78_verified_incremental_hardgate_20261013.zip
export R77_PARENT_ZIP=/path/to/RAZR_SLIDE_R77_verified_incremental_hardgate_20261013.zip
export R76_PARENT_ZIP=/path/to/RAZR_SLIDE_R76_verified_incremental_hardgate_20261013.zip
OPENBLAS_NUM_THREADS=1 bash R79_RUN_ALL.sh
python R79_VERIFY_PACKAGE.py /path/to/RAZR_SLIDE_R79_verified_incremental_hardgate_20261013.zip
```

`R79_RUN_ALL.sh` 会检查父包 SHA256/CRC，重生所有数据，独立进行 90 位数值检查，运行 35 项正负研究测试。它**不会**修改父包、OEM CAD，亦不会对 USB/电源或 OLED 进行硬件验收。

## 关键文件

- `src/r79_accel_robust.py`：起停解析不等式、稀疏 LP 见证、连续区间保守证书。
- `src/r79_independent_90digit.py`：不导入主求解器，独立高精度复核并检查 806 节点的分段恒等式。
- `results/R79_results.json`：必要界、示范参数、实际否决项。
- `results/R79_C1_piecewise_quadratic_witness.csv`：**非控制器命令**；仅供检查数学曲线。
- `results/R79_motion_interval_certificate.json`：连续区间而非仅格点的安全窗口证据。
- `docs/R79_hardgate_audit_20261013.md`：工程审计、证明、拒绝项。
- `docs/R79_vendor_RFQ_ADDENDUM_READY_NOT_SENT.md`：供应商询证增补草稿，**未发送**。

## 放行限制

若没有同修订版、可合法编辑的真实 OEM A/B、主板、导轨、双电芯/BMS、OLED/COF/FPC、连接器与禁布区，及厂商批准 FPC 的动态弯曲、卷储、寿命和张力，以及 USB 有线全程连续与双电池带载隔离台架，**禁止改 OEM 受保护 CAD、制造或宣传“实用手机完成”**。
