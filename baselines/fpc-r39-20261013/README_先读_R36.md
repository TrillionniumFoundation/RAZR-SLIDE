# RAZR SLIDE R36 — 研究级销头止退片与紧固件目录适配（NO-GO）

**产品方向不变**：等外形 A/B 舱目标、单约7英寸柔性屏、B向上滑、A优先电池，无外屏。严禁将本包用于生产、带电分离或对外称已合格。

本轮实际 CadQuery/OCC BRep 改型：B 舱左右后置加强座、M0.8 螺钉代理通孔、两片止退片。已验证它们能在局部刚体模型中挡住原 R35 细销的 0.05mm 抽拔；**但 M0.8 孔无真实螺纹，螺钉可自由退出，因此整体仍会失效**。小直径细销不兼容所检查的 DIN6799 标准 E 环，M0.8 方螺母尺寸也不能原样装入。

研究测试：继承 R21–R35 **559 项重新运行**，R36 **54 项新增断言**，总计 **613 项**。8 份完整 STEP 均已重导入；其中 5 份是故意失败的 GHOST。完整历史 R35 ZIP 853 个文件未改动，SHA256 `ee0b2eedc9f4b36c1e832b8d5dbdd3bbf121eb724e126d8fb84981f3ebd2a8c9`。

优先阅读 `R36_hardgate_audit_20261011.md` 和 `R36_supplier_gates_20261011.md`。主要可复算数据：`verification/R36_integration.json`、`R36_dynamic.json`、`R36_tolerance.json`、`R36_catalogue_fit.json`、`R36_faults.json`、`R36_STEP_manifest.json`、`R36_results.json`。

复算：在装有 CadQuery 2.8.0 / OpenCascade 的 Python 环境执行 `bash R36_RUN_ALL.sh`。若外部 R35 原 ZIP 可用，先做独立来源 SHA 校验；否则离线脚本只能按本包冻结成员哈希检查，**不能替代原 ZIP 来源验证**。脚本会重新生成 R36 BRep、故障数据、STEP、测试日志与哈希并执行 `r36_attest.py`。R36 原始文件外不存在电子载流或 OLED 实物数据。

结论：结构改型 + 危险故障探针完成，机械 M、电源 P、信号 S、USB U、显示 D 制造资格全部未通过；`manufacturing_go=false`。
