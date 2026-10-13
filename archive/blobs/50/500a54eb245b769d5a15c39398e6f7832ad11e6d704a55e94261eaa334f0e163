# R41 独立干净环境复算与制造否决记录｜2026-10-13

**独立复算通过仅指指定研究级 CAD/计算；制造资格依然 `NO-GO`。**

1. 使用 R41 最终交付完整包 `/mnt/data/RAZR_SLIDE_R41_FPC_full_verified_20261013.zip` 在**新的** `/mnt/data/R41_independent_replay/` 解包，并执行 `bash R41_REPRODUCE.sh`。该命令从包内原 R40 ZIP 重新恢复冻结 R38 研究 BRep。实际脚本退出码 **0**。
2. 原始 R40 完整包 SHA256 一致：`8df51e8e2c7a8c2733ddaa541eba9e85124d75d33c1a5e7b071fd1ec1f4db7ec`。
3. 本干净环境重新生成全部 **363** 组两轴数学案例、**72+35** 组中心线初筛与细筛、三布局×五姿态 **15** 个 OCC 带状实体、平面侧边 R15 U 回环以及五份 GHOST STEP。
4. `R41_motion_budget.json`、`R41_corridor_scan.json`、`R41_corridor_fine_scan.json` 的新旧输出**逐字节相同**。`R41_OCC_layouts.json` 中 **15** 个场景的实体体积、四组碰撞体积、包围盒、连接器占位与封装越界数值全部一致；STEP 整文件 SHA256 由于导出元数据/序列化差异不要求相同，不宣称字节一致。
5. 干净环境又跑 **42/42 项 R41 新断言**，退出码 0。**继承 R21–R40 的 766 项测试已在初始 R41 工程阶段从源码重新运行并记录，第二个干净环境默认重播只检查其既有收据，没有将 766 项谎称为第二次重跑。** 使用 `bash R41_REPRODUCE.sh --all` 才会在该环境重新跑历史测试。
6. 本次没有取得 OEM 机芯切除许可、真正柔性电路叠层/动态寿命、Hirose 准确端接布局、双电池功率保护或 USB SI 实物资格。**无任何 R41 走线布局可据此投产。**

详情及文件级比对见 [R41_independent_replay_receipt_20261013.json](R41_independent_replay_receipt_20261013.json)。制造 `NO-GO`，所有 GHOST STEP 只能用于碰撞复核。
