# 原数值资格复验与可复现的辅助载荷映射

本轮已实际恢复并校验7个原归档，按原 K/b/C、原 float64 运算与 1e-7 判据，重新执行 panel 原五探针、完整修正历史以及 frame 原五探针。随后执行原 H/restore 读回。没有重新求解或修改原系统。

| 原探针 | Panel 残差 | Frame 残差 |
|---|---:|---:|
| 0 | 9.9833377735581989e-08 | 5.6598979260758336e-09 |
| 1 | 1.990477778047551e-09 | 1.2689951358241719e-10 |
| 2 | 7.9778400558744992e-09 | 1.9311867265678982e-10 |
| 3 | 7.7998978509609027e-09 | 1.2438483918711836e-10 |
| 4 | 8.043638351779749e-09 | 1.7809635438880483e-10 |

Panel 验证 45 个原门、1262 条精确方程、36180 个候选行和7个未改变的精确锚。其最坏残差仍靠近原1e-7门槛；没有将它描述成更宽的误差裕度。

H读回覆盖两体各3885列，核对7770个原基底RHS和保存投影SHA。原 `ExactResponseCache.restore` 实际调用五个原有序、SHA绑定全场动作，最大相对误差 1.1659935073707673e-08，满足原2e-7门。原失败frame8:520块保留并排除。

历史未保存全部7770列成功全场，本轮也没有声称重算全部K乘积或一般逆算子。restore资格仍限五个原保存动作，未知或重排RHS被原合同拒绝。

## 新的确定性 loadG 运算

原 `R.T @ F` 在不同运行环境下存在末位差异。本轮从SHA绑定原loads中抽取4221项非零乘积，使用整数精确乘积与累加，最后显式执行一次binary64最近偶数舍入，得到新的版本化24项辅助映射。独立reader使用Fraction重新求和、检查24个舍入单元，并重新从原R/F提取每一项。

新映射与R9保存的正确舍入精确参考24/24逐位相等。它与历史BLAS映射有10项不同、与R9当前BLAS映射有6项不同，最大差均为2.220446049250313e-16。这些差异保留；旧seed没有覆盖，旧whole-seed逐位复现仍为false。

171个独立Fraction差分用例覆盖抵消、极值、亚正常数、最近偶数中点、正负下溢和最终溢出拒绝；24个原点积各5种乱序，共120次顺序不变检查通过。3种无效输入和4个实际篡改文件被拒绝；篡改文件保存在测试目录。

对表示矩阵在实数算术下作用于四个系数[-1,1]的情形，独读通过每行全部16个角点验证差值界。对历史映射，六行界依次为4.440892098500626e-16、0、0、0、2.0816681711721685e-17、2.220446049250313e-16。该界不包含下游QP/接触活跃集敏感性，也没有混用不同物理量的安全阈值。

## 范围与重现

本轮闭合原有限数值资格的当前执行读回，以及新辅助loadG运算的精确与舍入确定性。全seed的新版本、一般RHS逆算子、finite-QP断点续算、当前改型几何FE和G3–G5实物资格仍不在此次结果范围内。

当前Python3.12.14/NumPy2.3.5/SciPy1.17.0；没有冒称历史依赖运行环境。实际数值worker峰值来自自身getrusage，外部/proc只观测到嵌套launcher。两份最初命名错误的RSS字段及其独立纠正记录均保留。

原大归档由 `evidence/ORIGINAL_ARCHIVE_RECOVERY_IDENTITIES.json` 的精确名称、长度、SHA及持久文件身份恢复。新的小型包保留源码、原reader、每次执行报告、容量依据、失败记录、独立精确项和篡改文件，不重复塞入GB级原矩阵。

恢复归档后可执行：

```sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
python prepare_numeric_replay.py
python run_with_receipt_v2.py --receipt evidence/PANEL_NEW_EXECUTION.json -- python original_inputs/n13/source/current/readback_n13.py --input original_inputs/n12 --run original_inputs/n13/native/N13-v3 --output evidence/PANEL_NEW_READBACK.json
```

完整已执行命令见各 `*_EXECUTION.json`；`NUMERICAL_SCOPE.json` 为结果边界，`PORTABLE_MAP_INDEPENDENT_READBACK.json` 为独立数学核验。为避免覆盖既有证据，重跑请指定新输出路径。
