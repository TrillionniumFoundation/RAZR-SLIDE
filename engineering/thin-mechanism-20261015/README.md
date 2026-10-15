# 薄型机构：原生几何候选，非产品资格

当前源码为 `integration/thin_mechanism.py`，独立重读入口为 `integration/verify_thin_mechanism.py`。
沿用主干 69170884 的两组原生输入；不修改旧归档、旧几何或 `integration/assembly_inputs.json`。
同样保留23个零件角色，KEY、PAWL和止挡原接触核心没有缩放。重排簧座、支撑、盖件边缘和下层盖螺钉，
将局部 e 厚度目标从12mm改为6.6mm；通过扩大 q 平面占用而实现，不声称总体积或质量同时下降。

6.7mm深内腔仍是上一轮显式假设的自研空壳。两个机构使用各自一个整体刚体变换作排布研究，
不是把零件拆散拼进内腔，不是实际OEM安装基准，也没有证明KEY与B舱79.75mm/8.2mm整段运动相连。
机械固定到壳体的紧固件、工具完整进入/操作空间、预压夹具、载荷、材料、公差和实际电子件尚未完成。
弹簧仅沿用原标称占位尺寸，不表示加长止挡臂仍具有相同刚度或可靠回位。

本轮当前配置440项/25组，成功与失败以实际测试报告、原生重读结果及GitHub Actions为准。
`candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false`。
