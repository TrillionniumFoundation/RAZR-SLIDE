# RAZR SLIDE R34 — 前向装配真实**目录尺寸**信号器件的空间审计

**研究级 CAD。绝非可带电工作的连接器或制造放行。**

来源：`/mnt/data/files/RAZR_SLIDE_R33_engineering_package_20261011.zip`；以 `r34_freeze.py` 核查 706 项完整祖先成员，所有新资产使用 `r34_` 前缀，原版本不得篡改。

R33 原两个非导电 0.35 × 0.60 mm 微型盒槽无法容纳 TE 2199001-1。R34 删除了研究级销机构的实际依赖，**从 R32 无孔 B 壳体重新构建**可容纳 TE 官方 1.05 × 2.4 × 1.2mm *矩形目录外包络*的两个独立前向进料仓。这只是信号器件的占位；没有原厂 STEP、焊盘、A 舱配合、保护盖、机械锁止或任何电性能。

关键源码：
- `r34_parts.py`：B 原生坐标的 FRAME、POCKET、THROAT 与双侧目录尺寸代理。
- `r34_integration.py`：实际 BRep 融合/切槽；旧 R32 框架前端游离碎屑的实体移除；局部壁材见证。
- `r34_dynamic.py`：10 个参考姿态，沿 Y 前向路径 28 例；正上方 22 例中 10 例相交 **为被否决方案**。
- `r34_tolerance.py`：4 档假设误差、216 个三轴配置；±0.12mm 发生 42/54 个干涉。
- `r34_faults.py`：继承 36/64 机械危险逃逸与 3 个单点电源旁路，强调新件能直接从前方退出。
- `r34_export.py`：6 份装配 STEP，其中 3 份 **GHOST 失败姿态**。
- `r34_freeze.py`、`r34_inherited.sh`、`r34_geometry.sh`、`r34_attest.py`、`test_r34.py`：原始字节、历史回归和当前证据的独立复算工具。
- `R34_hardgate_audit_20261011.md`：完整结果和未放行项。

保留产品目标：同外形 A/B 舱，B 上滑，约 7 英寸单主屏，A 优先大电池，无独立外屏。当前 A/B 原生研究壳体尚不能证明成品外观件真正同尺寸。

`STEP imported`、`unittest OK`、`BRep valid` 都**不是**安全承力、电力供应、USB、OLED 或可制造性证明。`manufacturing_go=false`。
