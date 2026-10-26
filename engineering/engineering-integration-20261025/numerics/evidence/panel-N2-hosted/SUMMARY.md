# N2 原数值分解诊断：公开工程摘录

实际运行：[40207901134](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/40207901134)；功能源 `bec1c8d79a37b4ba387d606cd7ea1c5867f3f9eb`。

算法 `MMD_AT_PLUS_A`、threshold 1、SymmetricMode=False，AS 6 GiB。原日志定位为 `Can't expand MemType 0: jcol 312868`。五个原 RHS 均已保存，但分解完成、求解和残差回执均为 0。没有将分配失败写成残差失败或不可行性证明；AS 是唯一原因未获证。

原 K/C/五 RHS 身份、43 锁包与真实中断清理已经核验；完整原始 ZIP 的 SHA256 为 `9091b4cd0091bc9c7120772003a53fa2dc56eca392f0617d9bae7f8770a787fd`。完整原件由私有交付索引定位，当前文件只公开工程结论。
