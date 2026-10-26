# V4a：精确 Common 原件导出；原 V4 native 容量合同不变

V4 首轮 run `40279094567` 已结束：native 与独立 reader 成功，scientific export 因文件名 allowlist assertion 失败，partial upload 成功。导出 allowlist 漏了 producer 的 `-Common.brep` 大写 C。V4a 只修改导出器与说明，加入四个实际执行的 IO / 名称反例测试；原 producer、V2/V3/V4 算法、adapter、独立 reader、17 对、完整 q 域、1e-7 和资源限逐字节保留。原 run 未取消、未改字节。

新规则逐一列出原 producer 的真实文件名族，只有 V2 跟随 Common 的固定 `-Common` 后缀允许该大写。未知文件只记录 SHA/大小/固定拒收原因，symlink 不跟随，继续导出其余已审科学原件、写完整 MANIFEST 并 exit 2。JSON 中 runtime locator / 邮箱等原过滤不变。测试中的合成 BREP 字节只验证导出和 hash，不是几何结果。

原 always-upload 只读取 publish。本轮实际仅保留 2,110 B ZIP 中的独立 reader JSON 和第一份 fixed-input BREP，没有 MANIFEST、producer report、逐 call JSON、其余 BREP 或时钟。其完整 ZIP / 两成员已读回核 SHA。hosted reader 在导出前实际检查了 262 个 call JSON、1,632 个 BREP、524 个完整输入，重建五 probes / 760 个非 flex 材料检查；17 对为 10 clear、7 unresolved enclosure overlap，11,764 对未测。没有逐 pair 身份和时钟原件，不能猜七个 unresolved 的具体名称或补造容量数据。原报告与缺失原件无法从 partial artifact 恢复；V4a 为保留完整科学证据重新执行，并保留首轮全部上述事实。详见 `V4_FIRST_RUN_EXPORT_FAILURE.json` 和原字节 reader JSON。

以下为原 V4 方法与容量合同，仍适用。

# V4：真实 K1 材料的原 SLIDE 容量阶段

本阶段只测量 **17 个重点实体对的原完整 nominal SLIDE 域**，为后续 11,781 对执行提供真实容量依据。它不是完整产品全域或物理允许域资格，也不是 K1 双姿态通过结果的外推。

## 已取得的输入身份

K1 run `40276423445`、诊断 commit `78da3826a1cce029cb36b76555d6be7de2001ba2` 的 near/far 工程原件，分别由 artifact `12629939266`、`12631025559` 提供。两姿态均已取得实际 154 材料、工厂和独立读回各 11,781 对 clear、两个 KEY 完整材料重建和原 source/runtime 校验。

本阶段保留机械侧原 `K2_K1_BINDING.json` 的全部字节，仅以 `K1_BINDING.json` 命名用于通用材料前置条件。其 SHA256 为 `cffbd88792fee8acb3406a76120069ae5b65ce37cc9cbd81af9d5fa3b8fd38be`。每个工程 MANIFEST 和全部成员都重新逐字节核对，之后未改的 `frozen_key_factory_adapter.py` 再验证实际完整 clear 报告，导入两姿态的原/候选 q=0 KEY，双向比较才放行。没有使用 raw runtime 报告。

功能源码始终 checkout 原 S4 `dd7def6e6a4de9f47dc91ca2ab336fb1a8828560`、tree `cdd9e2c41216201b6cd04dd610d45fde80499045`。候选、S4 默认源码与已发布 V2、V3、V4 API 的字节均不修改。

## 原合同与执行顺序

1. 用冻结 adapter 生成实际完整 q=0 factory，仅替换两侧已验证 whole KEY；其余 152 体来自实际 factory。
2. 直接调用原 `verify_slide_native.verify_factory_laws` 与原 `validate_construction`。保留四个 whole spring 身份、原五组 factory 输入、每组 152 个非柔性完整材料有向差分和两个完整柔性材料有效性记录。这些有限 probes 只交叉检查源运动律，不代替连续包含证明。
3. 优先处理七个 `B_SHELL`/telescope 对：L_TELESCOPE_2、L_TELESCOPE_3、L_TELESCOPE_3_CAM_LOWER_FLANGE、L_TELESCOPE_3_CAM_UPPER_FLANGE、R_TELESCOPE_2、R_TELESCOPE_3_CAM_LOWER_FLANGE、R_TELESCOPE_3_CAM_UPPER_FLANGE。
4. 然后处理四个同侧 KEY/STOP、四个 matched SPRING/STOP 以及两个 panel/KEY 对。

全部从原 `q=[0,12]` 开始，原 profile 分段、非零 epsilon 间隔和 midpoint 子分割参数 2 完全保留；原实现的叶深度可到 3，每个持续 unresolved 的实体对可有 36 次调用。完整 154 材料和 11,781 pair slots 一直存在，17 对全完成时仍有 11,764 对明确 pending。

名义域包括两侧独立 slot flanks、两侧独立 telescope joint 控制；KEY/crosshead offset、descent、tabs 等取原 nominal SLIDE 合同值。它不覆盖全部实际机械独立允许域、机构分支选择、恢复力或其它工况。

每个 source specification 都从原 Contract 重新生成，不复用历史 clear。当前实际材料先走 V4 的有余量新边界快筛，必要时进入冻结 V2 完整面 carrier；匹配接触对使用冻结 V3。原 whole-material、有效拓扑、有向体积、Common 上界、每个完整实体对的总 `1e-7 mm³` 判据、4,096-region cap 均保持。错误不能被子域 clear 或相反 frame 覆盖。

## 容量依据与限制

原完整 C2 SLIDE 实际耗时 1,236.487 s、峰值 RSS 540,286,976 B，五个 factory probes 在约 132.907 s 完成；93.57% 顶层调用由 axis gap 退出。L2a 的 89 个困难原调用实际两 worker 共 352.192 s，最终 frame regions 共 44,313，实际 Common 检查 1,901；此前没有新方法的逐 case 时钟。L3 两 worker 共 151.927 s。K1 near/far 工厂实际 250.851/337.095 s，独立读回 206.102/274.861 s。这些是已完成任务的观测，不能直接保证本轮 1,800 s 完成。

本轮保留原 SLIDE 单 worker 的 1,800 s / 1,536 MiB RSS、6.8 GiB 共享不可回收内存、启动 200 MiB 普通可用盘及新增 1,536 MiB 内存、运行 100 MiB 可用盘门槛。原 owned-process ready/release 握手和外部 in-flight wall/RSS 中断保留；supervisor 的阈值未提高。hosted 外层沿用 L2a 的 40 分钟 job、2,220 s 命令截止和 2,250 s 监护截止，额外时长用于安装/准备/导出，不增加 native worker 的预算。

每个 specification 保存整体调用秒数（含输出）、V4 算法秒数、每 frame region 构造秒数、每个 Common 秒数、region/check 数、fresh bounds 和结果。未测完的量保持缺失，不能用平均值冒充逐例实测。若预算停止，已完成调用原件、活动区间以及全部 pending slots 保留；本阶段不能靠缩域或放宽门槛获得绿色结果。

下一步只有在本轮实际容量资料支持后，才冻结完整执行方案。已有九分片备选为七个 telescope 对各一片、305 个涉及 KEY 的对一片、其余 11,469 对一片，所有片统一材料、源码、精确域和 pair-index 合同。它仍需全 11,781 对无重无漏的实际 union 读者，不是现在已执行的结果。

## 证据与独立读取

每个调用的两件实际输入、V3 whole carriers 和负控制、V2 第一个拒绝 carrier 及可取得的后续 Common 都保存 BREP，并绑定签名、字节数和 SHA256。后续 Common 明确是新计算，不冒称原失败 Boolean 对象。未知拓扑失败保持异常及已能取得的原件。Common 接受不使用绝对体积。

调用 JSON 单独按 SHA 保存；紧凑区间树仅引用调用身份，避免每一步重复写出全部大 carrier 审计。完整 pair inventory 独立保存。原五组 probe、源域及资源记录保留。`read_capacity_v4.py` 在独立进程、不导入 CAD 的条件下重建原 Contract、分段和完整求和，检查调用/输入/保留 BREP 的哈希及符号记录；它不是第二几何内核或新的 BREP 几何重算。

导出采用明确科学 allowlist。只保留报告、调用 JSON/BREP、pair inventory、独立读取结果、源码与输入 binding、限定 controller 投影及逐成员 MANIFEST。源/runtime 私有快照、命令、环境、日志、个人或本地定位信息不导出；若科学 JSON 意外夹带运行定位信息，保留其 hash 与省略分类并使 export 失败，不静默发布。

准备期已执行四项纯控制（含真实原 154 名称表）和语法/嵌入字节校验，机械侧独立核对了 adapter 到原 probe 的接口。此时尚无本轮 native 容量结果；workflow success 也只能表示该容量诊断完成且原 postguard/独立记录检查通过，不能表示全部产品 clear。
