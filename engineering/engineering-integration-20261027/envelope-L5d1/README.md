# L5d1：逐项记录 Python 绑定缺项的 Boolean 诊断

本次修复的是 L5d 新观察器的接口错误。原有几何失败、原材料、原判据和原容量守卫保持。诊断即使到达六次构建末尾，也不能宣称连续包含、原七实体对、current 七实体对、11,781 全对、真实 15 维域或 K3 通过。

## 实际失败和证据来源

L5d head `40a4357903b63051578940d14ff8ee6426c04388`、run `40470232086` 实际启动了 2/6 次 Build。原 CadQuery cut 再次抛出已匹配官方锁定源码的 null 异常。底层 Cut.Build 返回，实际参数是 RunParallel=True、FuzzyValue=`1e-7 mm`、NonDestructive=False、CheckInverted=True。随后新的状态方法 tuple 提前求值 `op.HasErrors`；锁定 Python 绑定没有该属性，导致观察器退出，IsDone 和 Shape 都没有采集。

这次 73 字节 AttributeError 的 SHA 为 `0d165a7bfff2eda8cf99c280369ddd2d8e168339998513e9320546305e752797`，与公开类名、源码属性名和标准 Python 缺属性格式相符。原失败不是一次新的几何结论。完整原包 118,351 字节、SHA `3258aaeb818b57a145ba3565ae1f784169c5b68124c797bfabf290a6528f856a`，39 个 manifest 成员加 manifest 已逐字节、CRC、完整集合独立读回。原报告和失败索引均保留，具体见 `L5D1_PREDECESSOR_FAILURE.json`。

## 这次改变的观察器

`checkpointed_native_method` 把属性获取本身放在已记录操作的 lambda 中。IsDone、HasErrors、HasWarnings、GetReport、Shape 分别观察；缺项保存异常类型、文本 hash 和字节数，并继续下一个独立观察。C++ 声明的 public using 不被当作 Python 绑定已暴露的证据。

在同一个已经 Build 的对象上，另尝试公开的 Builder 和 DSFiller 接口，记录各自的错误、警报和受控 alert 类名。最多两个子算法对象、两个 gravity、每组 32 个类名；新增零次 Boolean Build。子算法报告明确标注为 child-only，不能填补或代替 wrapper 的未知字段，不能把未知状态变成 pass。

实际 Python 能力按有界白名单采集：每个 wrapper 12 个已知公开方法名，每个子算法 3 个，最多 90 次属性存在性观察，另记录受控 OCP 类型名。不递归对象、不调用 dir、不导出对象内容。方法不存在与原生状态值分开：`exists=false` 表示接口缺项，`HasErrors=null` 保留未观测；不会把它写成没有错误。

null 仍不 cast、不赋零体积、不构造空 Compound。非 null 的 cast 失败现在也进入最终 selected false，这修复了独立源审发现的一个退出遗漏。每个非 null 材料接受仍依赖原 whole_material 完整拓扑、正向有向体积和原 Common 上界门。

新 raw observation 使用 `raw_mass_accessor_value` 加类型对应单位。Solid 是 mm³，Face/Shell 是 mm²，Edge/Wire 是 mm；Compound 不能只靠容器类型确定单位或材料资格。只有原 whole_material 门接受的值可以作为实体体积。原 L5c/L5d 报告字段按原字节保留，本次不追改。

## 没有改变的范围

实际输入仍是 L5c 完整 52-member 科学原件，`L5D1_INPUT_BINDING.json` 与 L5d 绑定逐字节相同。八个实际几何文件、两份失败 STEP、两个坏 root 和原 L5c 报告均保留。六次 Build 仍为原 cq.cut、原材料 raw Cut/Common/反向 Cut，以及单位 box 的合法空和非空 Cut 控制。每个实际材料操作重新导入两个原 BREP；不变更 fuzzy、尺寸、位移、方向或 non-destructive 默认值。

原 19 个 L5 科学源码和全部 S4 源未改。supervisor 仅更换诊断标识：1800 秒、1536 MiB、共享内存 6.8 GiB、起始盘 200 MiB、运行盘 100 MiB、host 2220 秒、job 40 分钟和拥有子进程的生命周期保持。最多 32 几何文件、8 MiB 保存后停止上限、4 MiB JSON 仍相同；保存后检查可能超出一个文件，不是写前硬界。

上一轮只执行了两个 Build，耗时 3.58290157 秒、峰值 RSS 506,241,024 字节；L5c 完整操作诊断耗时 4.114908292 秒、峰值 517,107,712 字节。这些是容量依据，不是其余未测操作的时间保证。

完整观察流程与通过原门分别记录。任何所选原门失败或缺失仍 exit 2，always exporter/upload 保留可用科学原件。`original_null_failure_repaired`、`conservative_continuous_containment_proved` 始终为 false；是否能进一步修复，必须依实际 kernel 状态和原材料证据决定。
