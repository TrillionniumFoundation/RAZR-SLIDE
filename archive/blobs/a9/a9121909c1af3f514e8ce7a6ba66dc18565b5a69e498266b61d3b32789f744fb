# R65 OEM / FPC laboratory additional data request · READY_NOT_SENT / 尚未发送

**Status**: Draft technical requirements only. No email submitted, no NDA/authorization inferred, no customer/order commitment. Send only from authorized project identity through verified vendor channels.

## 中文：FPC 路由与台架数据的新增签发要求

请在 R64 原有 12 类原厂数据之外，提供第 13 类独立的 `FPC_kinematic_material_route_witness` 路由见证。须由获核验的 FPC 厂商签发者使用经独立渠道核对指纹的 Ed25519 公钥签名，与同一版 `OEM_A_fully_finished_shell_native_CAD`、`OEM_B_fully_finished_shell_native_CAD`、`FPC_actual_stackup_neutral_axis_dynamic_radius` 三份发布包原始 `release.json` SHA256 绑定，注明项目使用许可、具体物料编号、接口修订、共同 datum_set_id 与安装基准/禁止修改区。

请提供真实 PCB 焊盘中心、起始切线、应力释放夹位置；标定**同一条导线**的材料站位索引与总材料长度，在 B 舱 Y=0→79.75mm、终点 Z=−8.2→0mm 的典型与最坏状态列出每个站位的三维世界坐标。A 端世界坐标应恒定，B 端逆 `(0,s,q-8.2)` 平移后应回到同一个 B 本地锚点。必须同时提供连续全程的有限宽厚体积扫掠、弯扭应力计算、贴合外壳/电池/主板/OLED 禁布区，以及同一材料与版本的动态最小半径许可。

30 万次 FPC 双轴台架测试：请对每个独立样本提供样本/批次、独立 run_id、测量系统/校准报告/夹具照片、签发允许电阻上限、每循环计数与同循环铜连续电阻（带严格 UTC 时间及签发最大通道配对毫秒偏差）、签发测试机器最大周期频率、首/末周期与整程连续采样/波形、实际电流/温湿度/扭转、丢失接触时间阈值、负载、失效定义、试后失效分析。**首尾两个采样点不能证明 300,000 周期之间没有瞬断**；请提供原始仪器链和校验数据。

## English: additional signed route and fatigue data

In addition to the original twelve R64 evidence classes, please provide a separately signed `FPC_kinematic_material_route_witness` bound by the raw SHA-256 of released A and B enclosure CAD and exact FPC stack-up releases, with identical assembly-interface revision and datum-set identity. Include authentic PCB pad anchors, tangent constraints and strain-relief features, stable material-station indices, a constant total material length, and world-coordinate XYZ for the **same physical copper trace** along all slide (79.75 mm) and normal docking (8.2 mm) states. Inverse-transform the moving B anchor by `(0,slide_s_mm,dock_q_mm - 8.2)` to demonstrate a single B-local coordinate. Include finite-width/thickness OCC-compatible geometry, true sweep of the full continuous motion, bend/torsion fatigue properties and verified no-cut protected areas. The project cannot accept synthetic or re-optimized per-pose endpoints as solder pads.

Please also supply per-specimen and instrument-traceable 300,000-cycle real measurements: independent run ID, signed maximum resistance, maximum paired-channel timestamp skew, signed maximum mechanical cycle frequency, raw voltage/resistance waveform with dropout threshold, DUT batch/stack-up, tested motion fixture & load, calibration, and the complete failure criteria. Sampled CSV endpoints alone do not prove uninterrupted copper continuity.

**No OEM reply, signed release, authorization, specimen or lab qualification has been received at R65.**
