# 当前研究入口：背板承剪导向已接入，真实轴向锚固与结构资格未闭合

当前新增生成器integration/panel_shear_key.py，原生重读integration/verify_panel_shear_key.py；
前序cover_backing.py、pawl_box_guide.py及历史负对照保持原样。
证据engineering/panel-shear-key-20261015/DELIVERY_VERIFICATION.json。

两条背板一体低导向只新增12.65625mm³；框架、螺钉和全部运动锁止件不切削，25模板/79实体、24模板不变。
原朝向纯X取隙±0.02mm接触框架，±0.03mm阻挡。不能把背板保持绝对固定：
背板0.02、外盖0.02与PAWL相对外盖0.05可叠加至所试方向0.09mm，非完整自由域/公差保证。

功能提交955e120本机完整678项/31组及本候选标准full通过，源码字节前后不变；
八个基准工作状态、十六个整组偏移状态及两端整段X包络通过。云端因账户启动限制未执行，不能写成托管通过。

六个Z5.5mm单位载荷需框架+固定螺钉反力才能平衡；只用框架接触不行。
额外42个真实载荷面观测仍是有限法向模型，非实际载荷/预紧/分载。
下一刀优先完成四颗框架螺钉的真实连接规格、轴向保持和背板/框架变形预算；
原简单上方整装入问题、全方向锁止、真实OLED/B储屏/FPC/主板/双电池及细长连杆仍未闭合。
实际材料/载荷未知值保留，candidate_go/fixture_fabrication_go/manufacturing_go均为false。
