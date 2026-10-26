# EC1b：按实际 SONAME 补齐三个固定官方依赖

EC1 首轮与 EC1a 均在原 kicad-version 先决失败，未执行 native DRC。EC1a 已实际读取两个目标的完整 ldd 分类：kicad-cli 缺 libmbedcrypto.so.7；_pcbnew 缺该库、libGLEW.so.2.2、libjxrglue.so.0。原失败分别保留，既有 E3 中同 S4 源的 native 真 pass 不被这些环境失败覆盖。

本次仅向原 34 条固定包记录后追加三项，不替换任何旧条目：Ubuntu noble amd64 的 libglew2.2 2.2.0-4build1、libjxr0t64 1.2~git20170615.f752187-5.1ubuntu2、libmbedcrypto7t64 2.28.8-1。Ubuntu 官方 InRelease 的 GPG 签名、其绑定的完整 Packages.xz SHA、三个完整 DEB 的 bytes/SHA 均已实际核验。通过标准 dpkg-deb/readelf 在内存中读取控制记录、ELF64 AMD64、SONAME、NEEDED 和所需 ABI 版本；未执行这些库，也未保存或公开 runtime 原包。具体原始来源 URL 与认证摘要见 OFFICIAL_PACKAGE_SOURCE_RECORD.json，逐 ELF 结果见 NEW_PACKAGE_ELF_AND_DEPENDENCY_READBACK.json。这里的 member 字段是官方包内相对成员名，不是现场运行路径。

新增直接依赖中的 libjpegxr.so.0 由同一固定 JXR 包提供；libGL.so.1、libc.so.6、libm.so.6 已在 EC1a 的实际 ldd 中解析。该证据只支持 SONAME 依赖闭包与选包，尚不证明新 worker 的全部版本符号解析或 KiCad 导入成功；仍由原 version/native-readback/native-drc 检查实际决定。

原 34 包共 90,574,234 B，EC1a 已完成下载、解包及失败版本调用，共 12.3324 s；新增下载 578,006 B，三份 data.tar 合计 1,699,840 B，官方 Installed-Size 合计 1,886 KiB，规划增加 4 MiB 磁盘余量。原 4 下载线程、90 s socket、单包 60 s 解包、930 s verifier 与 25 min job 上限不变，不能由此前版本失败阶段时钟预测后续 DRC 时钟。

run_ec1.py、export_ec1.py、diagnose_ec1.py、其六项纯投影测试、原 34 包 JSON 均逐字节保留。五个 S4 原检查/设计源和原参数、版本门、DRC、资源守卫不改；workflow 只新增固定包 JSON 与精确 preflight，原 launcher 仅改为读取扩展包清单。Ubuntu runner、原 apt 步骤、导出/诊断流程、always-upload 科学白名单不变。原包仅留 SHA/核验过程；没有新增任何 raw runtime 公共投影。

本次准备阶段未执行 native ECAD；所有资格仍由实际原检查及可读回原件决定。软件 continuity/DRC 也不等于 OEM 端子、真实 OLED/COF/FPC、动态弯折或物理 G3–G5 资格。
