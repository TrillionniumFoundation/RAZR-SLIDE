# R12：G3 → G4 → G5 的事件、样件与时序合同修复

这次修改修复资格传递的实现缺口。没有进行实物试验，没有填入未知阈值，
也没有将合成测试记录记作 G3、G4 或 G5 通过。

## 实际问题与修改

原 G4 只从采样表收集失败，未处理采样表以外的分类失效记录和维修／换件事件；
原 G5 已处理这些项目。现在两者共用同一条事件处理路径：失效、未测、维修和
换件分别保留。真实报告的失效即使缺样本或附件，也不能被 `unknown` 覆盖；
缺附件另加缺证状态。维修／换件破坏同装配连续资格，但不自动记作失效。

原前置报告只比较样件字符串、提交和部分源码散列，缺少原装配记录与阶段时序。
现在要求 G3、G4、G5 使用同一个完整设计绑定，使用逐字节相同的原装配记录，
并检查原件内的零件、材料批次、工艺、固件、装配身份与本次声明一致。
同一个 specimen 名称下的固件更改、维修或换件不能继承旧记录。

阶段顺序同时约束采集和通过审查：

- 前一级采集开始 < 采集结束 ≤ 通过审查完成 ≤ 后一级采集开始。
- G5 同时重查 G3 → G4 的内部顺序，不能只检查二者都早于 G5。
- 缺原件、缺决策时间或缺采样结果时，前置资格为 `unknown`。
- 顶层 `pass` 与内部失效、未决、未完成覆盖或维修记录相矛盾时拒绝。

G3 保存全部判据；G4 的 `criteria` 保存异常项，所以成功的空 G4 列表不能
被错误当作缺证。G4 空异常表必须同时有 `sampled_criteria_status=pass`、
正的观测数量及完整非空采样覆盖。独立审查发现并修复了第一版实现对该正常
情况的过度拒绝，失败记录保留在相应 before-fix 文件中。

## 现有记录如何适用

必须在任何新实测之前冻结一个各阶段共用的完整 `design_binding`。它同时保留
G3 的 `artifact_roles`／`routing_candidate` 和 G4/G5 的 `candidate_id`、
全部源码及 native payload 身份；不能分别生成互不一致的部分绑定。
现有模板仍是起点，缺的实际角色和材料原件需要真实输入，不能由此脚本推断。

G4/G5 每个 `as_built[specimen_id].specimen_record` 引用原始 G3 as-built 文件。
该原件需预先包含 `qualification_assembly`，其 `parts`、`material_lots`、
`process`、`firmware`、`assembly` 五条记录与后续阶段的记录完全相同。
缺少这个明确对应关系的旧文件保持 `unknown`。原有 G3 角色观察、原件、
日期和设计绑定继续检查；没有将新聚合字段替代原角色证据。

G3 结果现在保留已校验的原装配文件引用及采集起止时间。其现有
`preregistration_verification.reviewed_at_utc` 可用于链条时序；G4 新结果
保留经检查的 `qualification_reviewed_at_utc`。两种时间同时出现时必须一致。
程序只验证文件内容和声明的一致性，不认证仪器、审核者或附件的现实真实性。

## 验证记录

原 43 项 G4/G5 测试首先全部通过。新增八项针对性反例在修复前产生七个断言
失败及一个缺结果字段错误，原日志保留。第一次独立复核的四项反例、第二次
独立复核的决策时间及判据一致性问题，以及 G4 空异常表回归均保留。

追加 donor 复核前的针对性执行包括 62 项 G4/G5 测试、8 项当前 G3 绑定测试和 57 项既有 G3
资格合同测试，合计 127 项通过。独立审查另执行七个记录准入控制，分别验证
合理接受、缺证为未知及矛盾拒绝。独立审查的 source SHA 与实际提交源码绑定。
这是修改范围内的验证，没有宣称全仓回归或实物资格。

测试命令：

```sh
python -m unittest tests.test_product_qualification_contracts tests.test_g3_current_candidate -v
python -m unittest discover -s integration/product-study-tests -p test_qualification_contract.py -v
```

本目录原日志和 `../independent-review/qualification/` 保留修复前后结果。

## 封存前追加：原始 donor 身份绑定

先前 127 项测试和审查报告保持原样。追加审查发现，原件的五条装配角色虽已绑定，原始 donor 身份仍可能被外层 plan、wrapper 和接口声明同时改名。现在原装配文件须在顶层或 `qualification_assembly` 中明确给出 `same_donor_specimen_id`；两处同时声明时必须相同，并与 plan 和当前 wrapper 的已知 donor 一致。缺原始 donor 为 unknown；矛盾或非法声明拒绝。结果另外保留 `as_built_donor_specimen_ids`。

六项新增控制的修复前执行确有四项失败；修复后 68 项 G4/G5、8 项当前 G3 和 57 项 G3 既有合同测试共 **133 项通过**。新的源码与日志身份见 `SOURCE_AND_TEST_READBACK_DONOR_FOLLOWON.json`，原始 127 项证据不覆盖。所有 donor 例仍是标记清楚的合成记录，绝非实际 donor 取得或实物资格。

追加独立审查实际执行 G4/G5 共用路径的 12 种 donor 配置；其中三个原控制的修后重验已包含在 12 种内，不另计为 15。外部 `verify_binding` 与 `product_inputs` 被明确隔离，真实原件/SHA、身份准入、前置资格及结果合并路径未替换；该审查不声称重新执行完整量测流程。报告见 `../independent-review/qualification-donor-followon/FOLLOWON_REVIEW.json`。
