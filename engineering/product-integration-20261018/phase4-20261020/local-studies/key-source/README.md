# 独立 KEY 闭合端帽局部研究

本目录不会改动 EP4 或共享仓库。默认仅计算标量；`--native` 才从明确给定的完整原生仓库读取 SHA 固定的工厂与真实母体。是否执行和是否接入总装由实际 EP4 结果决定。原生结果可以为失败，失败材料与原始来源都应保留。

## 唯一候选

右侧旧输出槽中心线 C=(6.5,78.25)、D=(20,64.75)，外半径1.1、内半径.425、槽片Z1.2..1.6。新候选把 C 改为 (7.15,77.60)，保留 D、内槽和槽片高度；新近端外半径.95，沿中心线1 mm内渐至原1.1。

外轮廓的实现是精确两圆盘凸包：设切向 T=(1,−1)/√2，法向 N=(1,1)/√2，E=C+T，半径坡度a=.15，则共同外切法向为 `−aT±sqrt(1−a²)N`。以 C/E 两圆柱及四切点四边形挤出形成近端凸包，再接 E→D 的原半径1.1 capsule。最后减去一个连续闭合的 C→D 内 capsule。没有根据任何 Common 包围盒裁槽。

新的外轮廓在X=6.20止步，给12 mm中心带留下名义.20 mm侧距；近端名义径向壁厚.525 mm。该尺寸没有公差、强度或材料依据，不是制造余量。

原生脚本还对**完整新 KEY**（含保留的真实母体与全部 arm/tab）读取精确边界，分别以右侧 `minX`、左侧 `−maxX` 检查 signed-X 内缘至少6.2 mm。只有这一项实际通过后，才能对全部材料位于 `−6≤X≤6` 的对象给出名义至少.2 mm的 X 向分离；理想 KEY 仅沿 Y 平移，因此该单独分离关系不随q改变。它不覆盖越出此X域的实体、制造公差、强度，也不替代把新KEY放回整机的全外场检查。

## 保留与材料账

- 实际母体来自 `cam_coupling.parent(side+'_KEY')`，并记录 mounted archive、manifest与项目源身份。
- 先用旧槽、原臂/横桥/立柱/上片和实际母体重建旧 KEY，与实际 `templates()[side+'_KEY_YOKE']` 做双向原生差，避免只按一组相似数字重建。
- 新 KEY 只更换闭槽几何，保留所有原臂/tab/母体材料；分别检查一个有效正体积实体、母体无丢失、原导向材料无丢失、旧/新槽与原臂的正体积连接。
- 从沿槽1 mm的E点开始，使用预先定义的定向检验域验证远端材料双向相等。此检验域不用于切改候选。
- 新闭帽填入一部分旧槽空域，因此必须同时保存 `removed-material.step` 和 `added-material.step`。不能宣称这是单纯减材，也不能继承旧候选的所有外场结论。

## 槽、flank与有限捕获验证

实际新槽必须识别到两个半径.425的内圆柱端帽，以及相距中心线.425的两个原生内直面。脚本还检查新槽与整个内 capsule 的 Common，防止 arm/tab意外封堵槽。

理想连续参数采用：q∈[0,12]、`dx∈±(.025 sqrt(1+(12/79.75)²))`、槽法向偏移n∈[−.025,.025]，且 `dq=dx−sqrt(2)n`。销相对 KEY 坐标为 `(7.25+q+dx,77.5−q−dq)`。沿槽投影对这些参数是仿射函数，极值由参数盒顶点给出；最近端最小余量约.080668012 mm，远端也为正。半径.4的完整销颈因此位于内槽半径.425的侵蚀胶囊内。

原生检查包含：

1. 左右手、四种flank极值的**完整 q 范围销颈精确 capsule 扫掠**，以及法向再越程.01 mm的正干涉对照。
2. 从实际 CROSSHEAD 截取并与预期源几何双向比对的有限销颈及上下法兰；在q=0/12、四种flank上检查正常高度无正交叠、轴向±.01 mm均有实际材料阻塞。
3. 一个对全参数成立的有限圆盘见证：位于销中心沿N偏移.55 mm处，半径.05 mm。它全程在槽壁内并落入法兰环材料；原生在参数端点验证其在轴向越程交叠中完整保留。上下法兰的实际厚度、加工与装入锁固工艺仍未合格。
4. 原臂各矩形材料在完整理想输出偏差区间的精确平移扫掠，对实际父背板中的导向件检查。新槽使用覆盖整个q区间的保守外 capsule 平移包络验证。包络发生正Common时只能说明这个充分排除方法失败，不能把包络多余材料称为候选真实碰撞。

所有正Common、双向差材料与完整新旧KEY都会输出STEP、SHA、总和逐solid的bounds/volume。任何无效拓扑或Boolean错误不当作无碰撞。

## PAWL与整机范围

脚本复核的是**旧 mounted PAWL 的完整1.1 mm回位包围体**，包括扩展臂的有限q位置、原矩形臂的完整q扫掠和新槽保守平移包络。该范围来源于历史 `verify_cam_coupling.verify` 的附加臂回位检查。

当前 serviceable/endpoint PAWL、tabs、肩销、弹簧恢复、闭合保持和自动复锁没有因此得到验证；报告中的 `current_PAWL_interlock_and_relocking_verified` 始终为false。真实机构的摩擦、受力、松手状态、制造公差以及正反程的强制驱动也未验证。尚未把新KEY安装回完整整机外场，不能声称FPC/OLED/壳体全场景通过。

## 运行

纯数学回归与报告：

```bash
python3 -B -m unittest -v test_key_endcap_local_study.py
python3 -B key_endcap_local_study.py --output /tmp/key-local-arithmetic-unique
```

只有主任务决定运行后，使用实际CadQuery解释器，传入冻结完整仓库与新外部输出：

```bash
"$PY" -B /absolute/path/key_endcap_local_study.py \
  --repo-root /absolute/path/RAZR-SLIDE \
  --native --output /absolute/external/path/key-local-native-unique
```

`native/native-report.json` schema为 `razr-key-endcap-local-native-v1`。`checks`逐项保留标准/实际结果，`artifacts`映射原生文件、SHA、体积与逐solid边界；每项检查后写`progress.json`。执行异常另存`native-execution-failure.json`。声明的局部检查全部通过时退出0；存在局部检查失败时保存完整报告并退出2。应同时检查 `all_declared_local_checks_passed` 和 `declared_failures`。局部检查通过不会更改任何整机或物理放行标记。

本交付脚本尚未在原生宿主执行；所有制造、样件、物理运行及全整机运动放行标志保持false。
