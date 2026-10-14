# STOW 回程与分阶段装入：名义几何修复，2026-10-14

本轮从 ce282a64 主张的 18 个 STOW 棘爪/外根座相交继续。开始时发现已有未提交的固定开槽连接片候选，先对源码绑定哈希并复制到独立工作树；原目录未动，既有候选和原失败没有被冒称为本轮新运行。

## 实际闭合的范围

新固定连接片 V2 只改变项目原创外根座，左右各保持单一有效正实体，外廓不扩大。每侧移除原材料 0.0256 mm³，完全位于已经声明的棘爪回程/装入碰撞包络内；新增约 4.549164792 mm³。其余零件实体不变；OPEN 不改；关闭修复仍保留原失败。连接片名义厚度 0.25 mm，不是已获强度或制造资格的实物。

新初始装配顺序为：内根座作为夹具边界 → 停放棘爪 → STOP0 → STOP1 → 外根座。实际使用完整有限直线包络检查，64 对阶段检查和 506 对静态检查均无正干涉。圆柱面采用明确保守的完整圆柱载体扫掠，不能把其正干涉当作必然的原零件相交；零干涉结论也只在所声明名义几何下成立。

独立新进程不导入设计生成器，对 64 个 STEP 完整载荷重读，反向重建包络并重算上述 64/506 对。另读取两份完整装配 STEP 的 92 个正实体，将 STOW 的 46 个叶节点与单件输出逐一对应，独立核对旧/新根座材料和外廓。仍为同一 CAD 内核，不称跨内核证明。

原参数、位置与判别阈值下，564 项动作采样和 184 项装配采样均实际复跑通过。原装配顺序的连续停放棘爪装入仍撞四个 STOP 对，这个负对照继续保存；原 184 个采样点通过不代表旧顺序连续可装。简单换序、扩大采样、单纯切除连接材料都不足够。

## 保留的失败与验证

首版完整运动开槽产生多实体，扩大连接片又产生四块纯新增材料孤岛，全部保留。V2 修改的是固定的新板坯边界，不按运行姿态修改根座，也不按最大实体筛掉原材料。独立材料布尔复核确认原材料没有在声明碰撞区外丢失。

当前 334 项 / 19 组测试通过。首轮在单核资源限制下 repository 组触发 300 秒墙钟超时，原日志和停止状态保留；仅增加执行预算并以普通低优先级重新执行，测试数量、断言和所有几何阈值不改。

## 尚未闭合

KEY/STOP 的耦合连续接触轨迹、真实夹具/夹持/工具、螺纹与预紧、材料刚度、公差、摩擦、捕获载荷及有限力回缩仍待完成。新顺序的夹具边界不能当作实物夹具。真实同版本整机内腔、完整布线端接组件、指定 OLED/FPC 和独立双电池/USB 电路没有因此完成。`candidate_go=false`、`fixture_fabrication_go=false`、`manufacturing_go=false`。

## 入口

`uv sync --locked` 后执行 `uv run --locked python -B tools/verify.py`。新几何入口：`integration/stow_installation_gate.py --output NEW_EXTERNAL_DIR`；原动作/装配回归：`integration/replay_continuous_sequence.py`、`integration/replay_continuous_assembly.py`，同样提供新的外部输出目录。独立反向复读：`integration/verify_installation_independent.py --repo REPO --receipt report.json --expected-sha256 SHA --output NEW_FILE`。

大体积原始 JSON 用 gzip 保留精确字节，原始/压缩哈希和长度见 raw-receipt-index.json。66 份项目原创 STEP 和 4 份拒绝候选 BREP 见 project-owned-geometry.tar.gz 与 geometry-manifest.json；不含供应商受限原始 CAD。所有关键运行的退出码和未截断日志均在 jobs/。
