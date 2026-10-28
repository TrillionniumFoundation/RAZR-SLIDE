# R4 新运行时独立实读审计

本审计由 `/root/r4_real_sources` 独立于恢复、构建、验证及 launcher 的作者执行。审计只使用 Python 标准库，未导入候选包、未执行原 CAD／数学任务、未重跑原 V2 合成控制，也未修改冻结来源。

实际命令：

```text
python3 -I -S -B r4-runtime/independent/audit_recovered_runtime_r4.py --runtime r4-runtime --original recovered-inputs/RAZR-R3-runtime-provenance-projection-complete-evidence-20261027 --out r4-runtime/independent/actual-readback
```

本次实际 exit code 为 `0`，审计运行 `12.630455690999952 s`，`completed=true`，`issues=[]`。全部逐项观察保存在 `actual-readback/R4_RUNTIME_INDEPENDENT_FULL_READBACK.json.gz`；JSON 报告绑定审计源码及所有被读控制输入。

## 实际核对范围

| 对象 | 独立实读结果 |
|---|---|
| 8,112 个候选 alias | 完整读取 1,226,421,880 字节；每项 SHA-256、size、literal symlink target 均符合当前冻结计划，relative、材料身份、owner、provenance 和 historical R3 source 均对应原 R3 map。当前新目标没有被冒充为历史原路径。 |
| 43 份生成 RECORD | 逐行核对成员、SHA、size、自身空 digest、无重复／逃逸／额外成员；完整字节还与恢复的原 R3 generated RECORD 相同。 |
| 候选目录与版本 | 精确 8,155 个文件节点＝8,112 aliases＋43 RECORD；无 pyc，43 个 METADATA 版本与原映射完全一致。 |
| old117 排除 | 原 117 个不准入目标字符串全部排除；53 个字节相同但路径不准入的目标均已改绑到有真实 wheel 成员接收链的新副本。原失败聚合仍为 false。 |
| 43 轮锁与 22 次真实接收 | 43 项恢复合同完整对应原 23 项复用评估＋20 项安装记录及原 uv.lock。22 个实际 wheel 的 172,641,744 压缩字节重新计算全 SHA／size；6,390 个选定成员实际流式解压并读取已提取副本，与原材料身份和接收记录逐项一致。 |
| 833／163 来源记录 | 对最终验证器实际记录的 833 个模块文件和 163 个命名空间位置独立重新分类，检查当前路径存在；候选模块还必须在 8,112 项 map 内。没有把此次记录审计称为第二次 native import 试验。 |
| 失败历史 | 恢复 v1 的 ttx.1 layout 失败、构建前缀遗漏、同合同验证拒绝、53 个旧目标拒绝四份实际记录均仍是 exit 2／completed false。没有改写成 pass。 |
| 六项资源限制 | 原限制值逐项未变；恢复／构建／验证三个成功 controller 的采样、启动准入、完成状态和退出结果对应原门。controller 时间分别约 20.73／5.24／9.65 s；与 worker 自测时间分开保留。 |

## Launcher 源码审查

审查对象 `run_qualified_script_r4.py` 为 7,840 字节，SHA-256 `1da31ba1c2eedee7c9a6c6c631a9aa66e0ac7ce92aca644a34ecc5e37dbc103b`。源码与绑定的冻结 entry 均完整审读；未发现会把实际不相等的当前文件身份误判为通过的具体缺陷。

执行前核对资格与合同、计划身份、全部 alias 目标和完整字节、精确文件集合、43 RECORD，并由原 entry 检查 `-I -S -B`、解释器身份和标准库起始搜索路径。执行后通过 `finally` 重新观察 alias／RECORD，要求 worker exit 0、无异常、8,112 项一致、43 RECORD 一致、文件集合一致，以及 worker／launcher／qualification／contract／plan／entry 身份不变。外来的已载 `site-packages`／`dist-packages` 来源会令完成条件失败。

这段 launcher 的 postflight 来源扫描针对安装包路径，不是对任意 worker 自行加载项目源码的完整 provenance 证明。前后观测也不构成运行期间不可写的保证。报告不作这些更强声称。

## 资格边界与原件保护

本次可支持的是当前 `candidate-v4` 快照的完整材料身份、指定接收链和记录来源资格。`historical_execution_requalified`、`compiled_kernel_formal_binding_verified`、`physical_qualification` 均保持 false。未推导连续几何正确、原数学探针通过或任何实物试验通过。

初次只读概览脚本曾把一个 list 类型的阶段回执按 dict 打印，实际 exit 1；随后按实际 schema 只读检查成功。这是独立审计准备中的显示脚本错误，另存观察记录，不是运行时失败或本审计程序的通过结果。审计程序首次实际执行即为上述 exit 0；没有覆盖失败运行。
