# R12 连续包络：填充语义的局部数学桥梁

本轮新增了可执行的精确纤维补满方法和独立检查器；对原 L1 case-011–019
的全部完整边界支持及原79个载体，验证了**在所述紧材料解释下，从完整边界
到完整材料的包含和严格分离**。实际新读回了27个原 BREP、79个原载体，并
另做79次原生 Common；全部为空，474个载体有向面环与正体积再次一致。

原生材料的实际集合身份、统一 compiled 几何误差、完整 B_SHELL region
union 和当前 K1/K3 全域 G2 仍未通过。这些字段在主报告中保持 false。
本轮没有重跑16帧完整包络搜索，没有重建旧失败原件，更没有把原 Common
的零值当作体积上界证明。

## 实际执行

| 组件 | 新执行结果 |
| --- | --- |
| 精确输入副本 | 202个文件、4,415,408内容字节；逐文件 bytes/SHA-256 绑定 |
| 新证书 producer | 9个原病例、3个精确控制；0.071384482秒、24,805,376 B峰值RSS |
| 独立数学与native读回 | 2.379074229秒、424,595,456 B峰值RSS；每次上限120秒/805,306,368 B/1 CPU |
| 完整固定体分层 | 121个Z原子区间/端点，842个严格载体-层比较 |
| 新完整盖面检查 | 44条完整二维pcurve映射；132个完整直线端点/顶点径向检查 |
| 独立原反例来源补审 | 0.031261239秒，绑定R11原外壳反例的精确材料和固定体 |
| 实际篡改负控 | 主reader 7项、来源补审2项，全部拒绝 |

时间为各程序实际单调时钟；RSS为实际驻留峰值。没有宣称独立外部计时，
没有把地址空间上限写成RSS。`producer-attempt1/`、`reader-attempt1/`、
`control-provenance-attempt1/` 保存本轮原输出；新输出须使用不同目录。

## 为什么这补上了一条数学缺口

R11精确反例表明：用六个薄外壳盒覆盖单位立方体的完整边界，仍会漏掉
`1/8`的内部体积，错过`1/64`的真实相交。原失败依然保留。新算法沿X纤维
把边界盒并集中的最左和最右区间端点之间全部补满，得到保守的完整材料
载体。实际反例补满后的体积为1，恢复的相交为1/64。

算法显式保留Y/Z单点格，处理投影只在端点接触的情形；不是仅计算开区间
格。另一个控制把Z厚度压到`2^-80`，仍得到严格正的完整体积`2^-80`，没有
舍零。原反例副本在`inputs/prior-hollow-shell-negative-control.json`；来源
补审逐坐标核对这个副本与新控制，避免只保留一个相同数字却换掉原几何。

九个原局部病例使用更紧的特化：source的全边界在完整凸斜棱柱内，原叶
覆盖的是整棱柱；fixed的全边界在逐Z圆盘内，径向射线证明把它提升为整个
紧材料截面的上界。完整证明及前提写在`FILLING_BASIS_R12.md`。

## 独立性、完整性与信任边界

独立reader不导入`filling_model_r12.py`或producer。原生抽取器只提供完整
原始字段；数学支持、partition完整性、零维格、径向分离、正体积和有向面环
分别检查。所有源与fixed都实际从原BREP重新抽取并与绑定inventory全字段
相等；原失败对象的metrics也重新读取并保持相等。

`check_filling_r12.local_filling`先调用已保存独立
`check_local_cover_r11.verify_tree`。它的`check_fixed`显式要求
`len(profiles)==len(fixed['faces'])`，并逐项核对`face_index`，不会用zip截短
隐藏一个面；新reader对所有实际原生pcurve抽取结果做全字段相等比较。
新检查随后增加每个盖面的完整二维pcurve映射支持，以及每条直线/每个
顶点的径向和轴向包含。

数学定理前提是：被支持的几何集合包含材料的整个真实边界，且材料是紧的。
程序验证了全部序列化表示的不等式、完整原件身份和实际native诊断。
它没有把native valid、无穷远OUT或一个公差数字升级成整个内核语义证明。
因此 exact-model compact-filling implication 与 actual-native qualification
在报告中是不同字段。初始q sweep、编译后 evaluator、当前K1/K3全运动域
和真实机械允许域继续需要独立证据。

## 复现

输入目录包含本次所需的全部原病例、载体、Common、旧报告和检查器副本。
`manifest.json`把历史绝对路径映射到可搬迁的相对文件；不修改旧报告中的
执行时身份。先从当前目录执行：

```bash
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python -B produce_filling_r12.py --inputs inputs --output NEW_PRODUCER
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 timeout 135s python -B read_filling_r12.py --inputs inputs --producer NEW_PRODUCER --output NEW_READER
python -B audit_control_provenance_r12.py --inputs inputs --producer NEW_PRODUCER --reader NEW_READER --output NEW_CONTROL_PROVENANCE
```

运行依赖为已记录的OCP native binary与Python标准库。软件环境身份、所有
输入hash和实际执行源码hash写在原report。载体沿用R11原79件，本轮新增
79次Common与数学证明；不把相同载体读回冒称为另一套新设计。
