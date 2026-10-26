# V2/V3 后续完整 SLIDE 接口与资源依据

## 当前结论与边界

当前可以交付的是一个具名、独立的后续接口、纯合同检查以及有来源的容量分析。**V4 接口尚未跑 native，K1 完整 SLIDE 尚未执行，也没有取得全域资格。** 原 S4 默认源码、原 L1 结果、已经发布的 L2/V3 方法源码保持原样。

L2a 的实际结果仍是 **89 个原调用、19 个不同实体对，4 clear / 85 conservative overlap**。L3 另对其中 **70 个原调用、8 个不同实体对**执行相关方法，70 个数值 clear；它们是 36 次完整 KEY/STOP 输入及 34 次完整 SPRING/STOP 输入。两个报告不能改写成一次“L2 全 clear”的执行。对照这两套新证据，剩余 **15 个调用、9 个不同实体对**：两个 panel/KEY 对的八个区间调用，以及七个 B_SHELL/telescope 对。两个 panel/KEY epsilon 调用的 clear 不覆盖其余行程。

所有 L3 carrier 总 Common 为 0，70 个穿透负向对照的 Common 为 `0.00013176096605022747` 至 `0.005808804816488513 mm³`。原阈值始终为 `1e-7 mm³`。case-014 的 `1.2793811944413415e-7 mm³` 继续保留为未解包络交叠，不能因接近阈值而改判。

L2a 和 L3 的科学 ZIP、每个 member、原 L1 JSON 字节、材料 BREP/STEP 身份、原静态 postguard 与完整 Common 求和已经独立读取核验。L3 的 1,018 个 BREP 文件均已逐文件哈希检查。这次独立读取没有另行导入 CAD；它不是第二几何内核。结果详见 `L2a_ALL89_INDEPENDENT_READBACK.json`、`L3_ALL70_INDEPENDENT_RECORD_AUDIT.json` 与 `L2_L3_COMPARISON.json`。

## 实测容量，及目前没有测到的量

| 执行 | 原调用数 / 不同实体对 | worker 秒数 | 峰值 RSS 字节 | 说明 |
|---|---:|---:|---:|---|
| 原 C2 完整 SLIDE | 13,770 kernel-call records / 11,781 对 | 1,236.487 | 540,286,976 | 154 个完整材料；原资源限内完成记录，但仍有方法错误/交叠 |
| L2a E17 | 17 / 对照表见 JSON | 124.749 | 516,096,000 | 含新方法 controls、原输入导入和证据输出 |
| L2a O72 | 72 / 对照表见 JSON | 227.442 | 515,018,752 | 全部保留 conservative overlap |
| L3 E17 | 6 / 6 | 18.709 | 511,983,616 | 保留非零 epsilon 区间 |
| L3 O72 | 64 / 8 | 133.219 | 512,557,056 | 整体相关构造和每调用独立原材料/负对照 |

原完整执行的五个 factory-law probes 在 **132.907 s** 时完成，含 760 个非 flexible 全材料对照和 10 个 flexible 有效性记录。原完整报告的 13,770 个顶层 call 记录中，12,885 个（约 **93.57%**）用轴向正间隙退出；483 个同姿态、284 个轴向扫掠、110 个仿射包络，其余八个顶层 raw 为 evaluation error。细看两 frame 共计有 25 个 error 节点，不能用八个顶层数量替代递归错误数量。

L2 本轮最终两 frame 共生成 **44,313 个 regions**，每调用中位数 282、最大 1,478；真正检查 Common 的 regions 只有 **1,901**。包括顺序包络中间阶段时，共生成 48,119 个 regions。这说明前置排除很有价值：大部分成本可能在生成后来没有用到的包络。

**本轮 L2/L3 没有逐 case 时钟。** 现有记录只有完整 worker 秒数和每 case region/check 数量。不能把 ZIP 时间戳、平均值或旧 L1 时间冒称为新方法的逐 case 实测。89 个困难样例的总平均约 3.957 s/调用，把它直接乘 11,781 会得到约 46,620 s；这不是全量预测，也不是容量证明，因为历史全量的多数调用早已由便宜的正间隙判断解决。

另一个真实风险是递归量：八个匹配接触实体对在旧完整报告中共有 144 个调用。V3 的完整相关构造使每个实体对有机会在完整 q 域直接结束，减少重复分割。但七个 B_SHELL/telescope 对由异常变为有效包络交叠后，按原 subdivision 参数 2 的实现（实际叶深度可到 3），每对最多可有 `1 + 5 + 10 + 20 = 36` 次调用。不能把旧异常的早停耗时当成修复后的完整耗时。

全部来源、原 report 哈希、原日志中的阶段计时、逐 case region 数与缺失的逐 case timing 字段，保存在 `FULL_SLIDE_CAPACITY_OBSERVATIONS.json`。这些是只读提取，没有重跑旧 CAD。

## 新调用接口怎样连接 K1

机械侧已经提供独立 `frozen_key_factory_adapter.py`。其 `load_keys(...)` 必须先取得 K1 near/far 两个真实 producer/reader 的完整 clear 见证、全部材料重建、154 个 STEP 读回、原 source/43-package 环境及确切 artifact binding，才返回 `VerifiedKeys`。不能用预案或尚未执行的报告填充该 binding。

它的 `full_scene(keys, nominal, cam, p, slide, descent, left_tab, right_tab, **kwargs)` 保留原全部独立输入。它先调用真实 S4 完整 factory，再逐侧用实际 KEY offset 算 q，将新的 factory 原 KEY 退回 q=0 后与冻结原 KEY 作双向材料检查，然后放置冻结的 candidate_q0。所有其他 152 个材料保持 factory 的实际输出；q 不夹取、不外延。该接口本身不证明全域，也不将 OLED/FPC/SPRING 当成刚性平移。

几何调用层是 `full_slide_api_v4.py`，主入口为：

```python
evaluate_specification(
    moving, fixed, spec, target,
    contract=source_contract,
    source_root=immutable_s4_checkout,
    p=original_product_assembly,
    v2=frozen_envelope_v2,
    v3=frozen_correlated_v3,
    original_postguard=original_frame_reader,
    budget_check=owned_worker_budget.check,
    emit=save_whole_v3_BREP,
    retain_v2=save_rejected_carrier_and_followup_Common,
    reference_frame="A",
)
```

`spec` 必须与原 `Contract.specifications(a,b,low,high,frame)` 新重建的结果完全相等；不能从旧结果挑出一个更小域。`target` 保留规范 a/b 名称和原 exact rational q 端点。调用层只按实际角色和原法则识别四个 KEY/STOP、四个 matched SPRING/STOP 对，其余仍由完整 affine 外包络覆盖。

输出使用独立 `razr-slide-specification-v4` schema。V3 放在 `correlated_result`，原静态 postguard 的作用限定为 carrier/obstacle；它不被塞进旧 raw 字段假扮成动态 `identical_relative_pose`。V2 放在 `affine_raw`，继续递归接受原 postguard 检查，另一 frame 的错误不能被丢弃。`FULL_SLIDE_API_SCHEMA.json` 明确区分这两种记录。`aggregate_complete_pair` 对整个源 specification 列表求和，每个原实体对只共用一个 `1e-7` 容积预算。

全量 owning driver 仍必须完成原五个 factory-law probes、原完整 spring 身份、所有 source/runtime/hash 检查、完整名字表、11,781 个固定 pair slots、原完整 closed partition、pair journal 与独立读者。V4 提供 `initialize_inventory`、`require_closed_partition` 与 `inventory_status`，缺失、重复、折叠 epsilon、遗漏 specification 或把 pending 当完成均会被拒绝。它没有通过这些 helper 自动获得完整 driver 资格。

## 前置排除与数值边界

V4 没有无条件让 11,781 个对都构造 V2 面包络。它先读取 **当前实际材料**的完整原生边界，包含 native tolerance；再对 affine coefficient box 作外向浮点乘加，并在两实体边界各加 `1e-5 mm` 的与 V2 相同尺度余量。只有整个外包络仍有严格正轴间隙时才 clear，否则进入冻结的 V2 完整边界 carrier 构造。

这比照搬旧极小浮点间隙更保守。历史 12,885 个正间隙中只有六个不超过 `2e-5 mm`；最小历史 gap 为 `2.842170943040401e-14 mm`。这个统计说明大部分已有快筛可能保留，**不证明** K1 新材料会得到同样的 gap，也不允许复用旧 clear。

外向 arithmetic 的说明只覆盖系数盒的浮点运算。OCCT 的 native bounds、几何变换、Boolean 与体积积分仍不是严格区间几何证书。此限制在新 schema 和每个 bounds record 中明确保留。原 4,096-region cap、拓扑/有向体积判据、Common 上界和整体求和阈值都继续生效。

## 建议的执行预算与停机行为

目前没有足够证据保证一个 K1 单 worker 全量任务在 1,800 s 内完成。可支持的下一步是：在 K1 loader 实际通过后，用这个接口执行一个具名容量阶段，保留每个 specification 的总秒数、region 构造秒数、每个 native Common 秒数、最终/中间 region 数、实际材料身份和全部失败原件。该阶段优先覆盖七个 B_SHELL/telescope 对、八个匹配接触对以及 K1 两个 panel/KEY 对的原完整 q 域，不能只测早停的叶节点。

若每对实际完整递归代价不能支持单 worker 预算，则使用**明确的新分片合同**，不伪称原单 worker 全量通过。一个可复核的分配是七个 telescope 重点对各一 worker、所有涉及任一 KEY 的 305 个不同实体对一 worker、其余 11,469 对一 worker，共九个分片、最多两 worker 并行。每片保留同样的 source/material/domain binding 和全局 pair index，原每 worker 资源上限不变；最终读者只在分片的 pair 集合无重叠、无缺漏且统一覆盖全部 11,781 对时承认完整执行。原病例中任意 positive/unresolved 继续存在。

这个分片数是避免一个长 telescope 递归占满所有工作的结构性方案，不是已经测出的总工期承诺。每 worker 的原硬限仍为：1,800 s、1,536 MiB RSS、6.8 GiB 共享不可回收内存、启动 200 MiB 普通可用盘/新增 1,536 MiB 内存、运行 100 MiB 可用盘。任何 inflight native 操作仍由独立 owned-process supervisor 限制。停止时所有未完成 pair slots 和已写证据必须留下；不得为了 job 成功减少域、放宽容积、删失败或不算其它材料。

旧完整输出的 report 为 13.74 MB、journal 为 25.12 MB。新逐 region 审计和失败 BREP 会增加输出，K1 两姿态输入的最终尺寸还需由实际 manifest 取得；因此输出空间不能只按压缩 artifact 大小估算。使用 hosted 容量阶段实测输出增量，继续保留原实时 disk guard。本地当前没有容量运行 CAD，也没有开始这个全量任务。

`check_full_slide_api.py` 已执行六类纯检查：完整/缺失/重复 11,781 slots，原 89 调用的 36/34/19 路由，非零 epsilon 闭区间与缺口拒绝，整体 Common 预算/负值/遗漏拒绝，affine 浮点外向结果覆盖精确有理数线性极值，以及独立 capacity-stop 类型。结果在 `FULL_SLIDE_API_PURE_CHECK.json`。这些检查没有导入 CAD，不替代后续 native 容量阶段或完整 K1 factory/domain 验证。
