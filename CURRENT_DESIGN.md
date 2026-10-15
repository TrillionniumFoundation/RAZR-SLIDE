# 当前入口｜目录螺钉适配，制造公差与载荷仍未闭合

新增 `integration/catalogue_roof_joint.py`、`verify_catalogue_roof_joint.py` 和 `manufacturing_fit.py`；证据入口 `engineering/catalogue-joint-20261015/`。父级端位槽、可拆控制、原传动及所有历史失败保持原样。

NBK SNZS-M1-5被选为尺寸研究候选，不是已采购/有完整公差的成品紧固资格。把四个承压面从Z0.55移至1.95mm，让目录5mm螺杆保持6.95mm终点、1.25mm名义母孔配合。只修改背板/导向沉孔及四颗螺钉名义包络；没有把厂家最大扭矩当安装值，没有模型化真实牙型、圆角、退刀或十字槽。

隔离环境20项新数学/输入测试与21模板子集原生检查已通过；未宣称远端主机执行。完整CI配置569项/31组及8组独立原生任务，结果以实际当前运行报告为准。目录名义模型无干涉不等于实际供应商上下限可装入。

旧约0.0034853mm根座间距仍小于明确的±0.05mm及未获资格的±0.005mm独立特征误差预算。完整实体在指定相对Y误差±0.020mm处产生反例；不把数学下界失败冒充实体反例。材料仅提出Custom630/H1075作为关键配合对的设计候选，要求选定热处理后精加工与检测；工艺能力、强度、预紧、摩擦磨损和表面处理仍未知。

`integration/assembly_inputs.json`和`roof_joint_load_inputs.json`不改写未知值。无实际采购、主机运行、加工、上电或供应商外发。实际OLED/B储屏/FPC/主板/相机/双电池及自动保持/展开端锁仍未闭合。candidate_go、fixture_fabrication_go、manufacturing_go均为false。
