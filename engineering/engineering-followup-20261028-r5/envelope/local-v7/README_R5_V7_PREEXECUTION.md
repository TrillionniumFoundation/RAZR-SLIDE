# R5 V7 平面外部通道：冻结与执行路线（预执行记录）

本记录保存 V7 首次正式数学运行之前的源、输入与执行路线。它不报告新的几何通过，也不把静态审阅或资源快照当作实际 worker 执行。

## 从真实 V6 失败叶开始

V6 的五阶段本地运行已经完成，完整条件模型结果仍为 8/16。V7 选择真实保留体积最大的 depth24 叶作为第一门：`case-028 / frame 1 / V6 root 76 / node 47`，旧 V5 定位为 `[28,17]`，有向正体积约 `0.0035074449511051124 mm³`。完整原叶、精确盒、原 full D 和祖先证书身份已写入 `R5E_V7_REAL_RETAINED_LEAF.json`。V6 的原失败、全局 4096 次 split 耗尽和全部原件保持不变。

新方法只为原 `plane_slab` 增加一个条件排除规则：把完整 `B = (C − D) ∩ old_stationary_face_box` 用 `Q = L(B − O)` 投影为闭 UV 盒，证明从整个 Q 到 `R = L(old_stationary_face_box − O)` 外部的闭通道严格避开完整 UV 边界覆盖。保留原 Line/Circle 全参数、端点、闭合不确定性盒和全部旧 3D 边、顶点；不使用采样点分类或绕行数猜测材料侧。

所有 UV piece 和 support 测试继续计入原共同预算。Circle 固定 64 段、Taylor 固定 24 项；全源最多 4064 个 UV piece、单面最多 225 个，完整 V6 有 4943 个保留根。新树仍最多 4096 次 split、相对深度 24，不增加原 `1e-7` 阈值。平面区域、原 primitive、trim 及 native 语义的模型前提继续明确未验证。

## 冻结身份

| 记录 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `r5-envelope/R5E_PORTABLE_SOURCE_LOCK_V7.json` | 8074 | `da61d0c1af1b6ac7ca2013990bf6cda43d1e8309a859b7bbfd7ec51abbf9971f` |
| `r5-envelope/R5E_V7_READINESS.json` | 5826 | `257c77acc6da8c5814e7f4c68be79e71769c6c844f70296f3aaf8d27e3dfbd6f` |
| `r5-local-v7/R5_V7_LOCAL_EXECUTION_READINESS.json` | 87074 | `3a230d6a501c4d746e986605fec540d24b3abc4e32a5362da6b01b5d9a55329e` |
| `r5-integration/r5-planar-v7-workflow.yml` | 2567 | `9e75b702a819750f24c75ea212ce8e964c1169429d71622d62240ea4ba7e7334` |
| `r5-integration/r5-planar-v7-workflow.template.yml` | 2524 | `1390d527cee13d80c87eafa5bb01439f77b60435662d1da5844e3d8b2ea7cd05` |

V7 锁覆盖 37 个 R5 成员和 3 个原 R4 supervisor 成员。新 producer/helper 与独立 checker 均已在冻结前完成源码交叉检查；新 checker 不导入新 producer/helper，而以独立 Horner/线性方程/严格通道实现重新核对新证书，并调用冻结的旧独立 checker 重验继承的 V5→V6 证明链。预登记的 5 个解析正控和 21 个解析负控在本记录时尚未执行，不能写成已通过。

## 本地只读快照与实际路线

`input-snapshot-v1/` 共保存 138 个文件、43,211,475 字节：38 个 R5 文件（含锁）、22 个 R4 源及公开输入、25 个原 V5 文件、53 个原 V6 实际输出。所有副本设为 0444，建立时逐一核对原件与副本，并在结束时再次核对；没有伪造 Git 或 Python 环境锚点。

建立快照时，普通可用磁盘为 200,183,808 字节，按原 cgroup 公式观察到 shared 不可回收量为 6,850,865,952 字节。加原 worker RSS 额度 805,306,368 字节后为 7,656,172,320 字节，高于原 shared ceiling 7,301,444,403 字节。这只是实际读取的瞬时资源快照，**没有调用原 supervisor 申请正式数学运行**，因此不是一次数学失败或实际 supervisor 拒绝记录。没有启动本地 V7 worker 或本地 launcher。

负责人据此将正式执行路线改为 Actions，并新增上述 concrete/template。两文件保持原 checkout/upload pins、仓库及 R5 分支限制、只读权限、`compute/RUN_REQUEST.json` 触发、55 分钟 job 上限、独立解释器和失败输出上传。新增 sparse 输入及 `--base-v6-root` 均指向原字节目录 `engineering/engineering-followup-20261028-r5/envelope/local/attempt-v6-1`。新产物名为 `R5-planar-exterior-v7-<run_id>-<run_attempt>`。

正式运行仍须最终独立静态读回、精确源发布和每阶段原 supervisor 实际准入。阶段依次为真实单叶 producer、独立单叶 checker、全 16 帧容量 preflight、全 16 帧 producer、独立全 16 帧 checker。只有第一叶满足原阈值、有正排除体积、最终排除证明实际使用新的 `u` 证书且独立 checker 通过，才允许后续扩大运行。若新的平面证书暴露原边/顶点 AABB 或其他真实阻挡，保留失败及未决，不改源、不提高预算来掩盖结果。

本记录时，V7 正式数学 worker、实际 controls 和 native 几何执行均为 0；全连续 G2 和全部 blocker 闭合均未取得。
