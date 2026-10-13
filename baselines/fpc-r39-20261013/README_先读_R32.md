# RAZR SLIDE R32｜后置双槽机械量规盒与承力截面试验

**工程状态：仅研究级 CAD，制造与带电装配均 NO-GO。** R31 冻结源包 `RAZR_SLIDE_R31_engineering_package_20261011.zip` 的 564 个成员全部复制、哈希校验且不在本轮覆盖。请先阅读 `audit/R32_硬门槛对抗审计.md` 和 `vendor/R32_机械电源USB与OLED实物门槛.md`。

## R32 与 R31 的真实变化

- R31 的 A/B 产品参考形态不变：两舱外形应等尺寸、B 舱向上滑、展开成纵向上半部、单块约 7 英寸柔性 OLED、无外屏、A 舱优先更大电池。现有研究 BRep 的 A/B native 本体外包围盒 X 等宽，Y 差 0.35mm、Z 差 3.4mm；没有带盖板的完整同尺寸 OEM 外壳可作最终一致性验收。
- R32 在 B 舱左右后方融合两个实体框架，从前端开插入槽。新 `R32_B_REAR_CASSETTE_BAYS.brep` 是实际 OCC 布尔得到的有效单连通 B 壳体。A 舱严格逐字节沿用 R31 `R31_A_POSITIVE_OPEN_SHELVES.brep`，不增删 A 侧钥匙。
- 每侧只放一只**无电矩形尺寸量规**（`r32_cartridge.py`）。它不是弹簧接点、连接器、限力机构、轴承、可换维修盒，也无真实 USB/电池主电源。
- 两侧新框架累计实际添料约 2.774739mm³、槽口布尔实减约 0.924mm³；取样格验证有实体材料存在，不等于连续最小壁厚/FEA/载荷资格。
- B 槽名义 X×Z 截面 0.35×0.60mm、A 端配对尚未设计；真实 TE 2199001-1 目录外包络在六种正交方向下均不适配，该器件最大 1.5A 且为 Signal 用途，不能构成主电源批准。

## 复算说明

本包提供 `r32_cartridge.py`、`r32_integration.py`、`r32_envelope.py`、`r32_dynamic.py`、`r32_tolerance.py`、`r32_faults.py`、`r32_vendor_fit.py`、`r32_export.py`、`test_r32.py`、`r32_freeze.py`、`r32_attest.py`，以及一次完整重算脚本 `r32_geometry.sh`。R32 依赖 Python/CadQuery/OCP + 源包所用的历史依赖模块。

1. 从该 ZIP 中按原相对路径解压到新、可写的工程工作树。
2. 将原始 R31 ZIP 放到脚本 `r32_freeze.py` 中 `SOURCE` 所标识的位置，或修改该常量为实际 R31 原 ZIP 的准确位置；不得以新包代替原 ZIP。
3. 运行 `bash r32_geometry.sh`，检查 `verification/R32_geometry_exit.code` 是 0。
4. 运行 `bash r32_inherited_tests.sh`（历史测试）以及 `OPENBLAS_NUM_THREADS=1 python -m unittest -q test_r32.py`。
5. 运行 `python r32_attest.py` 做数据、祖先、日志和制造 NO-GO 收据复核。

**注意**：工程包中的 7 个 STEP 里有 4 个故意记录危险 GHOST 姿态；成功导入 GHOST 不意味着危险消失。旧机械 `36/64` 联合失效、0.07mm 未拦截运动、无 A 钥匙假扣、限力回缩和双电池/USB/OLED 资格未关闭。不得用于直接带电接触测试或制造放行。
