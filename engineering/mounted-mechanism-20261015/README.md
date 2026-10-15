# 可拆背板与机构固定 — 2026-10-15

从已合并薄型机构 `287d37d035cf2497b69bfe6af0866b4531274e71` 继续。
源 `integration/mounted_mechanism.py`；独立验证 `integration/verify_mounted_mechanism.py`。

两侧各23个机构零件角色保留，只给两只内根座增加安装耳，原根座材料移除为0。
每套机构用一个刚体变换再沿Y移动6mm；接触核心、KEY、PAWL和名义螺钉不缩放。
A自研空壳拆分为框架和背板，增加四个机构安装点、四个框架安装点，以及八个M1×3名义实体。
沉孔、支承面、名义盲孔和框架连体柱均以实体表示。未表示真实螺纹、驱动槽、预紧、夹具、材料和制造公差。

首轮背板垫台与原框架侧壁相交0.7012486196104323mm³，源与完整导出保存在 rejected-frame-seat-v1.tar.gz。
修复用固定半径1.85mm、顶面z=1.2mm的定位沉台，非按每个姿态自适应切削。

本机20项新增测试通过，完整原生重读64份STEP、核对总成56个实体及46个原机构角色。
1540对静态、51项整板装入、440对名义螺钉路径、440对有限工具杆、144对新增局部运动检查通过。
原接触核心不变的接触证明沿用已合并薄型版本；没有冒称重新执行旧机械全部网格。
整板装入是暂时保持运动件条件下的20mm背面直线接近，螺钉路径是8mm背面接近；工具仅有限轴杆，不是已选工具/驱动槽。

完整A总成在原自研外廓内，由此前固定原生B外形整段扫掠包络验证79.75mm滑动和8.2mm就位无相交。
这只是固定接口与壳体空间检查，不是B驱动KEY的动作链。
当前KEY最大撤出12mm；一对一刚性直连仍有67.75mm纵向差和8.2mm法向差，故拒绝。
其他分段/失动/脱开重接拓扑未被这项反例排除，也尚未实现。

原实际成品输入登记保持字节不变。主板/相机、OLED/平面储屏、端接/FPC、电池/BMS和膨胀空间未集成。
机构6.6mm深、研究空腔6.7mm深的0.1mm总余量仍无公差、变形和温度资格。
名义耳根接触和支承面不代表可承载或螺纹连接已经合格；不可据本目录加工上电。
所有 candidate/fixture/manufacturing go 保持false。

## 重现

```sh
uv run --locked python -B integration/mounted_mechanism.py --output /tmp/razr-mounted-new
uv run --locked python -B integration/verify_mounted_mechanism.py --manifest /tmp/razr-mounted-new/manifest.json --output /tmp/razr-mounted-new/verification.json
```

输入全部为仓库内项目自有和已归档实体。输出必须是新目录。
托管工作流已纳入完整460项/26组和本模型原生生成/重读；运行是否通过以新增真实报告为准。
下一步聚焦B-to-KEY实体分段传动、反向重新接合与失效保持，并行进行紧固/安装耳载荷和真实器件布局。
