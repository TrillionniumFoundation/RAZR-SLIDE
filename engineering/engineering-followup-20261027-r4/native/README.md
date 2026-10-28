# R4 当前整件材料与原释放域证据

当前产品几何保持不变，所有新增和切除材料为 **0 mm³**。本轮实际完成 6 个完整原件的边界清单、62 个整件 KEY/PAWL 体对及独立读回，并将原 R3 标量见证中的 9 个具体碰撞姿态保留下来。原合同仍是 **tab=0 锁止、tab=3 mm 释放**，未把 tab=1 的过渡接触当作已经证实的结构缺陷。

- [完整结论与限制](R4_NATIVE_STRUCTURE_DOMAIN_REPORT.md)
- [原件 SHA、实际执行和门状态](R4_NATIVE_PUBLIC_EVIDENCE.json)
- [实际整件结果与连续源盒排除子域](R4_CURRENT_STRUCTURE_DOMAIN_PUBLIC.json)
- [原合同下的足够释放域、阈值及前驱](R4_ORIGINAL_RELEASE_DOMAIN_PUBLIC.json)
- [STOP/SPRING 源分段与真实模型缺口](R4_STOP_SPRING_SOURCE_MOTION_PUBLIC.json)
- [独立释放阈值复核的原字节结果](R4_INDEPENDENT_RELEASE_DOMAIN_REVIEW.json)
- [完整归档成员 SHA/CRC 清单](R4_NATIVE_SCIENTIFIC_ARCHIVE_RECEIPT.json)

## 完整科学归档

文件：`RAZR-R4-current-native-structure-domain-science-20261028.zip`  
大小：`15931402` B  
SHA-256：`a780ae352219fb131ca621f7cfad88865c513790146ade6b466f3470ea9bbaad`  
成员：`1195`，未压缩总计 `82292807` B。

科学归档保存全部实际原件、Common/差体、正体积反例、独立读回、四次运行的完整运行时和资源观察、原合同与源码，以及逐成员 SHA-256/ZIP CRC 核验。本目录是可公开审阅的投影；合同/结果投影中的路径名称与原始执行记录不同，数值和身份由原始记录 SHA 绑定。报告中的原始相对证据位置均指向该科学归档。`source/` 中保留实际执行/分析源码和独立审读源码；完整复现依赖归档中的原件、原源码与明确绑定的运行时，不能只按公开投影直接执行原 CLI。

## 放行状态

`all_blockers_closed=false`、`full_G2=false`、`G3=false`、`G4=false`、`G5=false`、`current_FE=false`、`physical_release=false`。

精确数学结果针对源盒/源支持条件。原生 BRep 集合语义、真实体积认证上界、所有编译变换、完整当前 factory 全域、全局壁厚/截面、公差/载荷/材料和真实保持重锁均按报告保留。此证据发布不重建缺失的 a11 Git 对象，也不声称恢复了原 R3 Git 祖先。
