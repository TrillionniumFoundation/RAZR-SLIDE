# RAZR SLIDE R37 工程包（研究版，禁止制造放行）

## 先看结论

- 977 个 R36 基线文件逐字节冻结，原 R36 ZIP SHA256：`0f5219663e6eae8c6817e6082c0d60172dcd9228386d3ec661fdbc9b9c2cf74d`。
- R37 新建左右一体 B 壳止退唇，各自与原 B 壳实质融合；健康状态对挡桥前向 0.05mm 退出形成 OCC 相交。
- **致命问题**：该刚性唇也挡住原挡桥从前方安装，且 ±0.05mm 相对位置下同时有安装卡滞和漏挡，存在单侧唇断裂逃逸。现无制造合格样机。
- PEM TA-10-075 具明确原厂尺寸但无法直接替换 R36 无螺纹薄板保持结构；供应商原生 STEP 未导入。
- 7 份 STEP，其中 4 份是**故障 GHOST**，用于对抗审阅，绝不可按图制造。
- R21–R36 旧单测已在独立 cell **613/613 通过**，新增 R37 **48/48 通过**；“通过”包含故障被正确识别。
- 制造、电源、USB、OLED 全部 `NO-GO`。4700mAh 与成品两舱同尺寸均未获得产品级实测资格。

## 核心源文件和数据

`r37_parts.py` → `r37_integration.py` → `r37_catalogue.py` → `r37_dynamic.py` → `r37_tolerance.py` → `r37_faults.py` → `r37_export.py`。

`verification/R37_*.json` 保存每一步原始几何计算和测试数据。`cad/R37_*` 为参数化 BRep / STEP。`audit/R37_R36_immutable.json` 保存 977 个祖先文件的成员校验。

## 独立运行

推荐 Python 3.13/CadQuery 2.8 环境：

```bash
export PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
python3 r37_integration.py
python3 r37_catalogue.py
python3 r37_dynamic.py
python3 r37_tolerance.py
python3 r37_faults.py
python3 r37_export.py
python3 -m unittest -q test_r37.py
python3 r37_verify_offline.py
```

若另有原 R36 ZIP 且放在与工程包相邻 `files/RAZR_SLIDE_R36_verified_engineering_package_20261011.zip`，可运行 `r37_freeze.py` / `r37_attest.py` 强化**外部原始 ZIP 身份**验证。没有原 ZIP 时，`r37_verify_offline.py` 只证明本包内 977 个祖先成员与封存清单匹配，不能冒充独立来源认证。

完整重新运行旧版本测试可执行 `r37_regression.py`，它在独立临时 cell 中运行而不修改原始文件；允许缺原 ZIP 时按冻结清单复制祖先文件执行（具体执行会重新生成日志）。

请先阅读 `R37_hardgate_audit_20261011.md`，再看 `R37_supplier_gates_20261011.md` 的制造否决标准。
