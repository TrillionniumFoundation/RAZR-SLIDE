# L5a：首轮 workflow 大小先决失败后的源码装载窄修

首轮 L5 run 40287815678 在 GitHub 解析阶段拒绝 660,075 B 的 workflow；实际提示为 500 KB 上限，0 job、0 check run、0 artifact、0 native CAD。原始失败单独保存在 L5_FIRST_RUN_WORKFLOW_VALIDATION_FAILURE.json。该失败没有产生任何原七例或当前七例的几何结果。

本次仅替换两份 prepare 块中重复的 21 个源码 heredoc。下载固定已发表 commit b3c9bef2abe0d7065063bc966ec2083616286bd5 下同仓库的 21 个公开源码/绑定/说明文件；每项精确 bytes 与 SHA-256 匹配后写入原外部 HOST_ROOT/l5 和 CASE_DIR/source/l5。无凭据、拒绝重定向、单请求 15 s、整段 90 s 加 5 s TERM 清理；原 2220 s 外部期限和 40 min job 期限仍包含这段时间，不增加任何预算。完整下载总字节和本地实际公开源读回时钟在 L5A_SOURCE_TRANSPORT_BINDING.json。

原 21 文件逐字节保留，S4 checkout、owned supervisor、host-cap/service-launch、native producer、两个 reader、所有控制、原 1e-7 整对和门、1800 s / 1536 MiB 及磁盘/共享内存/安装守卫全部不变。original → current 两 job 顺序与先决不变。源码下载失败仍是准备失败，不能成为几何通过。

本次仍只处理原七个名义 [0,12] 区间及其原 spec 的独立 Z 范围。不覆盖完整 factory 的浮点容差薄层、真正左右独立域、K3 新 panel、完整 11,781 对或物理 G3–G5。

原算法说明和原科学源码位于 ../envelope-L5/。本修复没有重写任何原失败或产生新的 native 结果。GitHub 官方 workflow 上限依据：https://docs.github.com/en/actions/reference/limits#workflow-file-size
