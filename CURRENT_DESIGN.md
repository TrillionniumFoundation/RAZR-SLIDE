# 当前研究状态｜盖件先定位的装配前段

本轮证据：`engineering/cover-admission-20261014/SUMMARY.json`及README。
入装执行器：`integration/cover_admission_gate.py`；原生输入：`integration/admission_native_inputs.py`。
运行运动基线仍保留`integration/keycover_bypass.py`及PR5原始几何。

两侧各七个装配阶段通过，均包括当时已放入的零件和有限夹具。第八步外根座闭合仍有实际碰撞，计划退出1；后续紧固和完整夹具退出没有执行。侧开定位口每侧移除0.04416mm³，保持/承载边界改变，闭合保持件尚未设计。

399项/22组单元测试通过。独立原生复读复现七段通过与闭合失败；全部130对既有运行包络重新计算仍零相交。旧564/184及64/506本轮未重复，历史结果不冒充本轮。

再生外根座对象构造面棱柱有未闭合线错误；本轮使用已绑定的原始STEP验证入装，没有据此宣布源端再生问题已修复。夹具仅有有限CAD几何，机架/驱动/保持力/材料和实际制作未获资格。

下一步：可闭合外根座/盖件保持接口、侧开定位口保持件、完整紧固和夹具退出；随后公差/载荷与真实整机输入。所有产品、夹具制造、整机制造放行继续为false。

历史：`engineering/keycover-geometry-20261014/`、`engineering/contact-motion-20261014/`、`engineering/stow-installation-closure-20261014/`及`engineering/workplan-execution-20261014/`均保留。
