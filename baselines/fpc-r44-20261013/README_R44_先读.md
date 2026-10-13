# RAZR SLIDE R44｜先读

状态 `candidate_go=false / manufacturing_go=false`。本工程包是**研究级空间筛选、否决记录**，不能直接制造、带电或宣称完成跨舱连接。产品约束：A/B 同尺寸目标、单块约7英寸柔性主屏、B上滑79.75mm 后 Z 坐实8.2mm、A舱优先电池；4700mAh 未验证。

本次新研究分支是**一条未接线的后背 XY 单 U 形带状 FPC**，宽1.2mm厚0.15mm、长120mm、名义 R16.5mm。`R44_hardgate_audit_20261013.md` 说明 121 位姿 OCC 空间线索、端接穿壳负例、原厂资料缺失及量产 NO-GO。

`baseline/RAZR_SLIDE_R43_FPC_full_verified_20261013.zip` 是精确冻结父档 SHA256 `d79c33b2a0e8eae2d05c5dc318b442bdffb1420e5361e87e0317a4d9191de7a0`。**完整包**包含该 94MB 父档；**增量包**不包含，需要将字节相同的父档放在 `baseline/` 后再执行。

复算命令：`bash R44_REPRODUCE.sh`（需要 Python 3.13、CadQuery 2.8/OCP7.9、NumPy；会解出多层祖先，可能占用约 1GB 磁盘、耗时数分钟）。也可按顺序执行 `r44_prepare.py`、`r44_rear_bypass.py`、`r44_dense_121.py`、`r44_feedthrough_probe.py`、`r44_clearance_stow.py`、`r44_budget.py`，然后运行 `python -m unittest -v test_r44.py` 及 `r44_attest.py`。

严格区分：本轮新鲜复跑 R43 21 测试 + R44 32 测试 = 53；R21–R42 846 项来自父包历史冻结收据而未本轮全量重跑。六份 `cad/R44_GHOST_*step` 均只是研究装配，A/B 原端接穿芯引出未解决。

独立清洁目录第二轮重算对照收据见 `evidence/R44_independent_clean_replay.json`；五份核心 JSON 可复现，六份 STEP 均在两轮重新导入有效，但完整文件哈希因导出序列化不同而变化。
