# 当前研究入口｜薄型机构名义几何已通过，实际安装接口未闭合

当前研究源码 `integration/thin_mechanism.py`；独立重读 `integration/verify_thin_mechanism.py`。
本轮证据 `engineering/thin-mechanism-20261015/SUMMARY.json`；功能提交 `9d420d882217d905c5e040bb142c5dd9d713d2ad`。
本机20项新增测试及两侧完整原生检查通过，托管CI实际通过440项/25组与新生成机构的独立重读。
后续追加的证据与说明不改变该功能源码；完整结果身份见同目录HOSTED_CI.json。

每侧23个零件角色保留，KEY、PAWL、STOP接触核心和标称螺钉未缩放。
通过重排簧座/支撑/盖件/下层盖螺钉，将e/q/r外廓从12×15.8×21.21mm改为6.6×30.6×21.21mm。
634对静态/占位、152对局部运动和642对声明装配/撤爪路径通过；新的根座保持名义上抬间隙0.1mm。
这些是STOW局部几何与规定的临时保持条件，不是实物载荷、夹具、工具操作或全手机运动资格。

两个完整机构以各自一个刚体变换进入上一轮假设的A空壳研究内腔，完整工作保守包络也在其中。
这不是OEM或成品实测配准；壳体固定紧固件和KEY到B舱的全79.75mm/8.2mm耦合仍未设计完成。
6.7mm内腔只剩0.1mm总名义深度余量，材料/加工/变形/热变化预算未知；q平面占用增大。
实际主板/相机、OLED及B平面储屏、端接/FPC、双电池/BMS与膨胀空间仍未装入。

下一刀：先做壳体固定接口、KEY与B舱耦合及完整行程，再把真实器件和受力/公差纳入同版本总装。
A优先大电池、B储屏、等外包络双舱、单约7英寸OLED、无独立外屏、4700mAh整机目标不变。
`integration/assembly_inputs.json`原字节与未验证字段保持不变；不能把研究假设填成真实数据。

旧宽机构 `integration/cover_capture.py`、空壳 `integration/phone_layout.py` 和历史失败全部保留。
`candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false`。
