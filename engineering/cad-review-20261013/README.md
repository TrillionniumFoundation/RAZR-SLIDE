# 2026-10-13 CAD 副审计与分支选择

先读 `BRANCH_COMPARISON_20261013.md`。选中 R50_20261011 为验证和修复集成基座，修复代码在相邻 `r50-repair-20261013`。本目录是独立副审计；`R45_CAD_motion_audit.json` 和 STEP 中的 R45 前缀不表示继承历史 R45_20261011 分支。

本次实际重算 R44 后背裸回环：121 个离散位姿×23 类研究障碍。加入 R37 未作 BM28 目录代理切削的原 B、现有双侧导轨和 cap/pin/keeper/螺钉代理及固定/运动桥叶。四个主障碍逐位姿使用 OCC 精确最短距离；其余检查真实 OCC 体积交叠，并报告 AABB 距离下界，不能把下界 0 当成接触或正净距。全部原始保护 BRep 与 OLED 代理均未删改。

新研究几何使用 q=0 精确圆弧和 q>0 显式参数/端导数样条，Frenet 截面帧取代原 corrected-Frenet 隐式端面倾转。所选数值方案有效，但 Frenet 几何帧不是真实材料中性面/端夹/扭转资格。只约束切向方向、不显式参数/导数的尝试产生 invalid OCC 实体，失败日志 `REJECTED_tangent_direction_only_run.log` 保留。

| 本轮新结果 | 数值/范围 |
|---|---:|
| 新硬轴裸回环发生体积交叠的位姿 | 0 / 121（23 类研究障碍） |
| 最小精确主障碍间距 A / B / OLED / 旧显示 FPC | 7.875 / 0.9510357 / 0.395 / 7.5605886 mm |
| 原 R44 坐实 B 宽轴偏离 XY | 27.9657426° |
| 新几何帧全样本最大 B 宽轴偏离 XY | 0.0350881° |
| 新 STEP 坐实样条 2001 参数样本的最小曲率半径 | 16.0228638 mm |
| 新研究 GHOST STEP | 6 份，各重导入 23 件有效实体 |
| 易轴截面 STOW OLED 交叠 | 2.0030464 mm³ |
| 易轴截面下侧 Z 包络超出（STOW / PREDOCK / OPEN） | 0.350 / 0.350 / 0.3526406 mm |

重要的是弯曲方向。原 R44 XY U 的 1.2mm 宽轴也在 XY，属于宽向平面内弯曲；0.15mm 厚度不能用于替代宽向极纤维距离。无层叠的理想 q=0 几何 w/(2R)=3.636% 与 t/(2R)=0.455% 仅为两个不同截面方向的运动学指标，不是真实铜应变或供应商允许值。将材料截面旋转为厚向易轴后，STOW 碰 OLED 且三代表姿态均超 Z 预算；PREDOCK、OPEN 的 OLED 交叠本身为 0，不能将 STOW 失败泛化成三姿态都碰 OLED。

这些计算没有接上原 PCB、没有产生 BM28 焊盘与应力释放、滚动导轨/后盖盒，也没有取得 OEM 可引出通道。离散 121 个姿态不是连续扫掠证明；负例不证明所有其它 3D 路线均不可能。

复算：

```bash
python -B cad_motion_audit.py --baseline /path/to/fpc-r44-20261013 --cache /isolated/cad/cache --out /new/output
python -B -m unittest -v test_cad_review.py
```

依赖 Python、CadQuery/OCP、NumPy、Shapely。本地本轮为 Python 3.12.14 / CadQuery 2.7.0，与旧基线 3.13 / 2.8 收据不同，环境在 JSON 保留。`prepare_inputs.py` 对各嵌套原始 SHA、CRC、成员数和安全路径校验，不调用旧不受约束的 extractall。

多机最小包可用 `--minimal-source --cache sources --out output`；逐项源文件 manifest 验真，`compare_receipts.py` 忽略运行环境、时间与新 STEP 序列化哈希，只对数值和几何语义比较（绝对容差 1e−5mm/mm³）。历史档案 SHA 仍须完全一致。

本轮新 CAD 审计 9 项通过；另重新运行 R43 21、R44 32 个历史/源码收据断言，不冒称旧几何整轮全部重算。所有失败记录、旧体积证据和原始归档保留。缺原厂、材料、电气、OLED 与实物安全资格时，`candidate_go=false`，`manufacturing_go=false`。
