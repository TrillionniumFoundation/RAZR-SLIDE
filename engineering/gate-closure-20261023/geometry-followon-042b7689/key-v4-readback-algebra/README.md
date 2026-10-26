# KEY 端点：已完成、已准备与被拒绝的执行

本交付绑定仓库功能提交 `042b768903cccbd7a0995317c8598401e0318e2a`。所有新增
文件都位于仓库外；没有修改原生产 profile、原槽尺寸、原阈值或原历史证据。

## 结果范围

| 项目 | 实际结果 | 仍未证明 |
| --- | --- | --- |
| v4 单 trial、原子检查点与严格恢复 | 当前五文件冻结，50/50 纯回归；独立源码复核通过；完整原资源守卫保留 | v4 尚未运行 native；六 trial/20,880 changed pairs 未完成 |
| 四个保存 STEP，attempt1 | 原预检拒绝；没有启动 worker；原回执和源副本保留 | 没有几何读取结果 |
| 同一冻结源码，四 STEP attempt2 | 在资源发生独立实测变化后重新授权；原守卫通过；2.351527 秒完成四文件读取、有效实体及完整体积核验 | 没有新 Common、整机生成、原始 pair ID 恢复或旧 trial 完成 |
| 原 STEP 支持的有限端点代数 | 六个完整投影重叠面片，名义间距 0.02 mm；完整原 dq/dx 耦合域保留；11/11 纯回归 | 完整 pin/KEY 与整场连续无干涉、全局第一硬止挡、物理资格 |

当前 50 项与 11 项是两组独立研究回归，均无 CAD 导入；它们不增加仓库已经完成的
1558 项 canonical 测试计数。v4 目录中旧 48 项回执及 reader 旧 18 项回执保留为
历史，不与当前计数累加。各独立复核也没有重复执行 native。

## 四个旧交集文件实际恢复出的数值

| 原文件尾号 | 完整 solid 数 | 读取体积 mm³ |
| --- | ---: | ---: |
| positive-01.step | 1 | 0.0012382062639602538 |
| positive-02.step | 2 | 0.0016509416852802346 |
| positive-03.step | 1 | 0.0012382062639599693 |
| positive-04.step | 2 | 0.0016509416852800477 |

四文件与原停止归档的 SHA 完全相同；每个完整根形状有效，未发现顶层非实体材料，
所有完整体积都高于原 1e-7 mm³ 阈值。读取使用原同一 CAD 内核，因此不称为独立
内核验证。读回守卫的 `peak_observed_worker_RSS_bytes=0` 只表示短进程没有取得
非零 RSS 采样，不能宣称实际峰值为零或实际 RSS 上限已被独立证明。

这些文件来源于旧被资源守卫以 125 停止的执行。旧 stdout 的 6792 配对仍只是
stdout 计数；旧 `report.json` 缺失。小型读回不补造 pair 身份，不恢复旧 trial 的
逐对完整性，也不使 v4 变成已执行。原正值的候选材料解释见有限端点分析 README。

## 冻结源布局与复现条件

归档内的路径除本说明、DELIVERY 与 INDEX 外，均保持相对于以下原工作目录的
完整相对布局：

`/workspace/scratch/95cd2986fdf2`

| 相对目录 | 用途 |
| --- | --- |
| `gates_audit/dev/key-endpoint-v4/` | 当前五文件、字段合同、50 项实际回归、原准备预检及独立复核 |
| `gates_audit/key-common-witness-readback/` | 原冻结小型读取器 |
| `run-key-common-readback-042b7689-v1/` | 第一次资源预检拒绝；原字节 |
| `run-key-common-readback-042b7689-v2/` | 第二次成功的原日志、原始 readback、全部来源/环境前后身份与执行源副本 |
| `gates_audit/endpoint-contact-analysis/` | 原 STEP 文本读者、有限代数、实际报告、11 项纯回归及详细边界 |
| `ci_audit/` | 两份最新只读独立复核 |

精确复现需保留上述路径，因为小读取器与纯代数 helper 的原冻结源码显式使用该
工作目录。将当前归档展开到一个新的同路径工作区，并恢复以下**已有独立交付**：

1. `RAZR-SLIDE/` 必须是原功能 HEAD `042b768903cccbd7a0995317c8598401e0318e2a`，
   所有 HEAD 绑定原输入字节完整，原 `.venv` 与 `uv.lock` 的 43 包核验通过。
2. `gates_audit/key-endpoint-042b7689-stopped-v1.tar.gz` 必须保持 SHA256
   `a4c9ec2f12c3e000ffbe281faaed7fa49ea0e125c0f815dafbcce860fc70c4aa`。
   将它的原成员恢复到 `run-key-endpoint-042b7689-v1/`，四个 STEP 位于其 `native/`。
   该原包没有被本交付修改或替换。
3. `gates_audit/canonical-controls-042b7689/canonical-control-domains-042b7689.tar.gz`
   必须保持 SHA256 `20026c869c81560681d95f81a7c1e37d4f9ff2221442b4c1e849a7618832eb56`。
   将原 `stow-pass-next-preflight-stop/stow-control-domain.json` 恢复为
   `run-controls-042b7689-retry1/stow-control-domain.json`，SHA256
   `9ac8e25082abd78b830ff3c853ecafdb49bb063bc736da206456964340ab49cb`。
   将原 `open-pass/open-control-domain.json` 恢复为
   `run-controls-042b7689-retry3/open-control-domain.json`，SHA256
   `e81980eb3d36e45ecc7f1e5d5bf1ffd50f0b0ef5de113dfae813264b77a64a2e`。

原始 v4 准备归档另有 SHA256
`a05ac043f7861ca3e3caf0cf3ed1171a4d5ecc92a74e3cb2e556866236e63f68`；本包携带
它原成员的同字节副本及原逐成员读回记录。它 README 中关于未来四 STEP 读取的
措辞保留为准备时记录；本说明与 attempt2 原回执记录随后真实完成的读取。

## 可复现命令

纯代数（已实际执行，无 CAD）：

```bash
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
  /workspace/scratch/95cd2986fdf2/gates_audit/endpoint-contact-analysis/endpoint_extension_research.py
```

从 `gates_audit/endpoint-contact-analysis/` 运行原 focused 测试入口：

```bash
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
  -m unittest -v test_endpoint_extension_research
```

四 STEP attempt2 的原实际 supervisor 命令如下；重现时 output 必须使用新目录，
原脚本会拒绝覆盖已有证据。90 秒、768 MiB 预留/RSS、原共享 6.8 GiB 及 ordinary
磁盘 100 MiB 守卫保持；完整 KEY 的原 2 GiB 起步预算没有改变。

```bash
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
  /workspace/scratch/95cd2986fdf2/gates_audit/key-common-witness-readback/read_saved_common.py \
  --output /workspace/scratch/95cd2986fdf2/run-key-common-readback-042b7689-v2
```

以下为 **尚未执行** 的 v4 最小完整单 trial 命令，用于获得真实逐对原始身份。
只有独占计算窗口和原始 2 GiB/256 MiB 起步预算满足后才应运行；原每 trial
1200 秒共同预算及运行 6.8 GiB/100 MiB 线均由 supervisor 强制执行：

```bash
/workspace/scratch/95cd2986fdf2/RAZR-SLIDE/.venv/bin/python -B \
  /workspace/scratch/95cd2986fdf2/gates_audit/dev/key-endpoint-v4/run_key_endpoint_trials.py \
  --root /workspace/scratch/95cd2986fdf2/RAZR-SLIDE \
  --expected-head 042b768903cccbd7a0995317c8598401e0318e2a \
  --stow-report /workspace/scratch/95cd2986fdf2/run-controls-042b7689-retry1/stow-control-domain.json \
  --open-report /workspace/scratch/95cd2986fdf2/run-controls-042b7689-retry3/open-control-domain.json \
  --trials STOW_OUTSIDE_HALF_BAND \
  --output /workspace/scratch/95cd2986fdf2/run-key-endpoint-v4-half-band-new
```

该命令仍然是一个有限姿态诊断。即使执行完整，它也不能单独证明连续端点域、
完整 G2、物理恢复力或制造资格。
