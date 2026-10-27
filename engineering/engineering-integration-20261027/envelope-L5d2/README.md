# L5d2：隔离可选子算法观察，保留原六次构建

这是一轮具名观察隔离。删除 L5d1 新增的可选 Builder/DSFiller 读取，继续原六项清单，目的是取得尚未执行的四项结果。它不是几何修复，也不证明这些可选调用导致了上轮崩溃。

## 必须保留的实际失败

L5d1 head `4927944f9ece18e0b5f67083ee9d8fb1da5d81a8`、run `40471621804` 的拥有子进程实际退出码为 `-11`。只启动了 2/6 次 Build。原 cq.cut null 再次复现；第一项 raw Cut 已保存 Build 返回、IsDone=False、Shape.IsNull=True，因此它不是合法空材料。新原输入 BREP、原失败 STEP 和旧报告仍保留。

wrapper 实际未暴露 HasErrors、HasWarnings、GetReport、Builder；DSFiller 暴露，子类型是 BOPAlgo_PaveFiller，其 HasErrors=False、HasWarnings=True。Fail alerts 为 0，Warning 类表没有通过原有界枚举门。最后完整保存第一项 raw probe 和两份 post-input BREP 后发生 SIGSEGV；真实崩溃位置及原因尚未定位。

原 worker 没有完成 finally，所以 report 内 source/runtime flags 仍是初始化的 false，完整 retention 终态字段缺失。controller 独立的已拥有子进程、外部源、锁定环境和通道收尾检查为真；完整科学 ZIP 的 41 个 manifest 成员加 manifest 已独立按 SHA、CRC、完整集合核实。两种证据分别保留，不把 controller 回执当成 worker 全部后置门完成。详细原始定位见 `L5D2_PREDECESSOR_FAILURE.json`。

## 本次唯一观察路径变化

不再调用 Builder 或 DSFiller，也不访问它们的警报对象。wrapper 的已知公开类型和十个明确方法名仍按有界白名单检查，最多 50 次属性存在性观察。属性获取本身始终位于 guarded attempt 中。不存在的 HasErrors/HasWarnings/GetReport 保持 None 或不可取得状态，不补成“无错误”，原 strict status gate 继续 false。

原参数、IsDone、Shape、Shape.IsNull、非 null cast 与原 whole_material 逐项记录。null 不 cast、不赋零、不创建空 Compound。非 null cast 失败仍 selected false。raw accessor 使用无单位 value 和独立类型单位，只有原 whole_material 接受的正实体值才可解释为实体体积。

## 未改清单和门槛

固定六次 Build：原 cq.cut、同参数 raw Cut、Common、反向 Cut、单位 box 合法空 Cut 控制、单位 box 非空 Cut 控制。每个实际材料操作都重新导入两个冻结 BREP；不更换微小材料、不改变任何尺寸、fuzzy、位移或默认 non-destructive 参数。原八个几何文件、两份失败 STEP、两个坏 root 和原 L5c 报告继续逐字节保留。输入绑定仍是同一 11,587 字节原件。

原 19 个 L5 科学源码、S4 和材料接受门都未改。原 worker 1800 秒、1536 MiB、共享内存 6.8 GiB、启动盘 200 MiB、运行盘 100 MiB、host 2220 秒、job 40 分钟及拥有子进程的生命周期保持。最多 32 个几何文件、8 MiB 保存后停止限、4 MiB JSON、每个可取得 wrapper gravity 最多 32 alerts 不变。保存后停止可能超出单个文件，不称写前硬界。

容量依据仍是完整 L5c 操作诊断的 4.114908292 秒和 517,107,712 字节峰值，以及 L5d 可收尾失败的 3.58290157 秒和 506,241,024 字节峰值。L5d1 的 3.311885492 秒、508,076,032 字节只是最后保存时值，不能冒充完整 worker 峰值或总时长；其 controller 经过时间为 6.234285214 秒。

如果本次相同六项观察隔离仍由 SIGSEGV 结束，停止此策略，不盲目追加次数。原所有失败、未测项和科学原件分别保留。即使六项调查到达末尾，缺失状态和失败原门仍 exit 2，always exporter/upload 继续保留科学资料。原七对、current 七对、全域和物理资格均未执行、未宣称通过。
