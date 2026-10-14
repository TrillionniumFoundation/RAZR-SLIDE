# 当前研究入口｜装配候选与尺寸参考分开

## 尺寸参考线

保留 `integration/keycover_bypass.py` 及 `engineering/keycover-geometry-20261014/`。原近端绕接结构的晚装盖件仍有历史阻塞；本轮不改写它的尺寸或旧验收。

## 新装配研究候选

`integration/cover_admission.py`；证据 `engineering/cover-assembly-order-20261014/SUMMARY.json`。盖件先定位、夹爪端部夹持、内根座侧向进入、棘爪下方进入、STOP依次进入、外根座闭合、螺钉与刀杆检查：左右22阶段/130对检查以及独立STEP复读零正干涉。运动130对及原564/184采样回归通过；385项/22组单测通过。

这不是原盖件的无损替换：封闭定位结构改成侧向槽，定位舌特征移除，远端绕接增加局部q方向3.5mm占用。原根座、KEY、STOP等44个非盖件零件独立比对不变。实际手机内腔是否容纳、新槽保持力、夹爪执行机构与力、临时保持、螺纹预紧和疲劳仍未知。

## 下一步

先将3.5mm和新接口放回同版本真实A/B机舱，验证保持/夹紧和预紧，再谈产品接入或实物资格。OLED/FPC、完整端接与双电池USB门槛不因局部几何通过而取消。candidate_go、fixture_fabrication_go、manufacturing_go仍为false。
