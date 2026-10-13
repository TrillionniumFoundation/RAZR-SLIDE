# RAZR SLIDE R35：后置加强轨＋可拆前挡桥的研究级工程审计

**制造、带电装配及宣传成安全产品：NO-GO。** 本包从 R34 验证 ZIP 逐字节冻结 783 个成员，不覆盖祖先文件。仍坚持 A/B 同外形目标、单 7 英寸主屏、B 向上滑、A 优先大电池；完整实际 OEM 外壳/主板/电芯和 OLED 均未取得。

R35 实际修改：B 两侧增加舱内独立加强轨、前向贯通的挡桥导向槽和横向销孔；一件可拆前挡桥装在目录尺寸信号量规的前端，一根可拆占位销穿过 B 壳和挡桥。**此销可轴向退出，无额外认证的卡簧/锁定件**，所以这里只产生几何阻挡与完整失效见证，未完成真正失效常闭。

项目入口：`r35_freeze.py`, `r35_parts.py`, `r35_integration.py`, `r35_dynamic.py`, `r35_tolerance.py`, `r35_faults.py`, `r35_export.py`, `test_r35.py`, `r35_attest.py`, `r35_inherited.sh`, `r35_geometry.sh`。详细数值参见 `R35_hardgate_audit_20261011.md`，外部供应商要求参见 `R35_supplier_gates_20261011.md`。

本工程中的所有 `TE_CATALOGUE_AABB` 都是未通电的矩形代理，不是 TE 原生 STEP。没有真实 A 舱配合导通件，更没有电池主电源/USB 安全连接器。七份 STEP 中的四份 GHOST 是故意保留的危险/碰撞见证，不属于可制造装配。

重新验算：在此目录内运行 `./r35_inherited.sh`（历史 509 项）及 `./r35_geometry.sh`（几何/50 项新增/审计）。需要 CadQuery 2.8.0 和包含原始工程树的本包；只要测试或证据缺失，不得宣称通过。
