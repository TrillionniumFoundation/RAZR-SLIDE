# R5 三维干涉参与体的谱系桥接

只读逐字节对比当前 R50 与历史 R44/R45 缓存的两舱 BREP，A/B 均一致。实际运行结果及三份源/清单 SHA256 见 `lineage_receipt.json`。因此新 FPC 圆角候选可绑定同一两舱谱系中的历史 OLED、显示 FPC、导轨和导向研究实体，覆盖完整历史参与体，而无需选择另一个 R39 变体。

OLED/显示 FPC 使用 `r44_rear_bypass.protected(s,q)`；导轨/导向件使用 `r35_parts.inboard_rail(side)` / `arm_guide(side)`，随 B 变换 `(0,s,q-8.2)`。详细额外参与体和桥片构造保存在冻结的 `strict-motion-audit-20261013/cad_motion_audit.py`。此桥接不提供 OEM 腔体开孔授权、受控 OLED 实体或装配/寿命资格；原 B 的历史头部切口仍未获授权。`manufacturing_go=false`。
