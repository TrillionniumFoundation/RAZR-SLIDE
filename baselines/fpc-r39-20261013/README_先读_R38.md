# RAZR SLIDE R38｜架构取舍：从外露滑动接点转向静态混合端接 + 动态跨舱柔性线束

**工程资格：研究级 CAD，NO-GO。** 此轮是架构转向与空间筛选；没有可工作的跨舱线路，也没有把 BM28 10 次插拔额定误当作 30 万次滑盖寿命。

## 与 R37 的实质变化

- 保留 R37 原始 1,043 个文件不可变，并在新名空间产生 R38 文件。历史 36/64 机械危险逃逸与三类单点带电 PCB 旁路不是通过换名称消失。
- R38 不继续制造 R37 刚性止退唇或使用 0.22mm 无资格保持销，改为对真实供应商候选进行静态舱内尺寸审核。
- 候选是 Hirose BM28B0.6-24DP/2-0.35V(53)，**静态永久配合**，跨舱理论上由连续 FPC 传输。已查询 OEM 官方料号和 STEP 下载入口；原生 STEP 未获取，实际 CAD 仅为 **6.12 × 1.5 × 0.6mm 保守目录盒体代理（含标称 0.6mm 配合高度；不等于完整 PCB/FPC keepout）**。
- 10 姿态证据只覆盖两端*孤立*静态零件代理与 A/B/OLED/FPC 旧名义几何。B 新位需移除原受保护 BRep 实体，尚未获得 OEM 授权，不能对外宣称主板空间可用。
- 纵向滑移 79.75mm + 法向就位 8.2mm 必须重画完整真实跨舱柔性线束，R38 已证明这组特定端点不能直接用固定双轨平面 U 环解决；其它三维柔性拓扑尚需验证。

## 快速复算（Python 3 + CadQuery/OpenCascade）

`python r38_integration.py` 生成新 BRep 和 `verification/R38_integration.json`；`python r38_faults.py` 生成否决故障矩阵；`python r38_export.py` 导出 5 份 STEP（1 份 GHOST）；`python -m unittest -q test_r38.py` 检查工程断言。完整历史回归由 `python r38_inherited.py` 在单独源 ZIP 副本进行，所有通过日志都以退出码和 `Ran N tests ... OK` 验证。

**单次脚本不带任何原生供应商 STEP、PCB、真实排线、外壳和电芯；模型验证通过不构成真实机电资格。**
