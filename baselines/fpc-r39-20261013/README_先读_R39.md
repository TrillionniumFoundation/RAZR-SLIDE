# R39｜请先读：这是一份失败证据充分的三维 FPC 研究包，而非制造放行包

- 源 ZIP 为 `RAZR_SLIDE_R38_verified_engineering_package_20261011.zip`，SHA256 `649c89711e5bd25a357fbac972d1c0e4ac8144841dd34e8b261cd67aa50bb7a6`，**1094 个祖先成员逐字节保持**；请勿修改或删除祖先。
- 三维数值脚本：`r39_path.py` → `r39_screen.py`；6 份非 OEM 的带厚度 BRep / STEP 由 `r39_export.py` 输出。
- 88 个有限场景的全量记录见 `verification/R39_path_screen.json`。全部四种路线不合格。STEP 6/6 能重导入，但全部属于危险 `GHOST`，不代表机械、电气或 OLED 合格。
- `r39_regression.py` 已从干净解包 R38 独立重跑历史 **697** 项；`test_r39.py` 新增 **49** 项；`r39_attest.py` 综合确认 746 项研究级断言，不等于 746 次真实样机试验。
- 单项完整 OCC Boolean 尝试见 `verification/R39_optional_OCC_diagnostic.json`；A 壳有异常负有符号体积，且其余五场景没有完成精确布尔求交，此阶段**不得算作六份完整布尔通过**。
- `r39_attest.py` 需要原始 R38 ZIP 路径；离线单包的内部成员哈希不能代替外部来源验证。
- 交付中的 `R39_hardgate_audit_20261013.md`、`R39_supplier_RfQ_20261013.md` 是工程判定与向厂商的资料请求。
- 当前仍然没有可通电的跨舱 FPC、没有双电池主电源、没有 USB SI 合格证据，也没有 OLED OEM 寿命证据；**制造 NO-GO**。
