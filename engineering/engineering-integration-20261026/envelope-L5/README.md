# L5：原七个完整伸缩材料的同轴分层连续包络诊断

本版本只在独立诊断 branch 执行，不改 S4 默认源码、K1 KEY 候选、制造体、原 Common / postguard / 1e-7 或原资源门。它先对 L1 保存的 case-011/012/013/014/016/017/018 全原件回放；后一个 job 才用真实双姿态全 clear 的 K1 whole KEY adapter、原完整 factory 与五个原 factory-law probes，运行这七个当前 whole-q 调用。

方法和容量依据见 `L5_METHOD_AND_CAPACITY_PLAN.md`。原七对合12个源圆环层，每个研究阶段12个 primary carrier Common，另有完整源重建、BREP/STEP 对照、Boolean 组成体包含、负对照和另进程 native 读回。这是以 V4a 七对252原调用、约999.067 s 的实测为基础的新算法试算，不预先承诺1800 s内完成全11781。

## 三类证据分别记录

1. `exact_xy_support_l5.py` 对最终 binary64 四角作精确 Fraction 半空间证明。ordinary / reversed、1 ULP 缩宽反控和负绕向反控已在纯算术中执行。它证明完整连续平面矩形的支撑包含；不是整个 OCCT 内核的区间证书。
2. `run_l5.py` 执行真实完整输入、逐层/source union 双向差、全部 carrier Common、整个实体对总和、真实负对照、原EXTRUSION材料直接控制、普通/反向/零/极小 capsule 控制。任何返回的临时桥、端盘、并体和差集在最终验证前保存实际 BREP。native 尚未执行时不写通过。
3. `read_l5_native.py` 在另一个拥有自己1800 s /1536 MiB限的进程中重新导入每个 BREP/STEP、校验几何、重新 Common、总上界和负对照。`read_l5_records.py` 再纯读取全部hash、原源分层与完整q合同、原静态postguard和当前阶段五probe。前者仍是同一个固定版本 CAD 内核，后者不运行 CAD，二者不互相替代。

## 原阈值与遗漏

每个瞬时姿态的 Common 上界为所有分层 carrier Common 的总和，加一次 actual−rebuild 的非负体积，再加 capsule Boolean 组成体遗漏体积。最后仅对整对应用原1e-7。即使这个体积门通过，若任一严格集合包含差集非空，也保留 `unresolved_source_containment`，不升clear。非空/无效/负向差集和预算终止分别保留。不会取 abs(volume)、跳过源材料、剪行程、丢tiny段或改原阈值。

原S4默认 `telescope_offsets=None` 与本原SLIDE明确传入 `float(Fraction(17,6))` 的reference不同；本L5绑定后者的真实caller，不替用前者。原whole材料和重建体必须逐次相互对照，当前B_SHELL包含全部加入和channel cuts，不复用旧STUDY的pass。

## 研究完成不等于clear

producer / reader 只有完整七例、源与环境闭合、全部原postguard都成功才exit0。合法的 overlap / source-containment unresolved可以是完整研究结果，必须保留实际分类。未测的11774对始终未测。不能由job成功推出K1全11781、独立5D/13D域、SEATING、K3、G2或实物放行。

## 导出与局部失败

生产者和另进程reader都先保存完整本地原报告。工程artifact只允许冻结命名的JSON/BREP/STEP以及具名源码，任何未知文件名只记录hash/bytes/受控拒收类别。原报告内唯一已review的绝对repo archive locator，经实际原manifest和内容SHA验证后，才转换为repo相对路径，输出带原报告SHA/bytes的 `report.engineering.json`。其余科学字段不改；未知locator仍拒收并exit2。即使拒收某项，其余合法科学原件和完整MANIFEST仍保存，always-upload不因export红灯而丢已接受原件。

本source保留原L2七个native控制，另直接读原case016的temporary EXTRUSION whole solid/face，以原同vector重现旧拒绝，再直接运行V2新路线。绕开旧分支、或新case通过，都不会把旧方法记录改成已修复。

容量：每个native worker1800 s、1536 MiB RSS、6.8 GiB shared；200 MiB启动盘保留、100 MiB运行盘保留、1536 MiB启动额外内存；新science输出128 MiB cap；每job40 min及独立2220 s hosted deadline。任何门触发均保持未决和剩余清单。
