# R50 选中验证分支的真实代码修复

来源为 `RAZR_SLIDE_R50_verified_negative_gate_20261011.zip`，SHA256 `86f226f9bce3a3f0659737327c7cc32415eed3b9be3f96f35a746ac32844dfd6`，41 成员。原始归档及所有历史基线未修改。原源码与修复源码哈希在 `source_provenance.json`。

原 `solid_intersection` 只对 compound common 执行 `isValid()` 检查；此前 R39/R41 已出现 `isValid=True` 却负体积的数值反例，因此不能把这个条件当成可靠净空判定。修复源码 `src/r50_full_span_finite_ribbon.py` 逐格调用 `src/occ_signed_volume.py`：所有参与体在 AABB 剪枝之前必须是一件有效、finite、正体积实体，保证一个位于远处的反向负体积实体或零厚度输入不能假报已检查的零占用；common 必须有效、finite、原始体积严格非负，且不超过任一参与实体体积加显式 1e−7mm³ 数值容差。**任何负值，包括 −1e−12mm³，都拒绝，不转成零净空。**

108 个相邻 loft 可自重叠，故新的各格 common 求和是逐格占用统计，不是真实实体 union、可切削材料量或对旧 compound common 体积的逐字等价替换。碰撞见证可以用于拒绝原路线；不存在由数值求和得到制造授权的路径。

复算使用隔离提取的、经过同一原始 SHA 链验证的 R50 工作树：

```bash
python -B run_repair.py --source-root /absolute/path/to/verified/r50/worktree
```

如果尚未提取，可先使用相邻 `cad-review-20261013/replay_selected_r50.py --prepare-only` 从该原包恢复独立缓存（附 archive、`--cache` 和 `--out` 参数；prepare-only 不运行额外几何）。`configure_source_root` 在导入修复模块后检查 R49→R48→R47 和原始研究 BRep 字节身份，不读取另一同名 R39 分支。

`run_repair.py` 重新运行原 R50 的 23 个历史收据断言、新增 10 个 guard 测试（真实 OCC 分离、交叠、包含、自重叠统计与非法 signed volume），以及 4 个 AABB 参与体检查（普通分离、真实 reversed body/cell 的负体积、远处零厚度 wire）。随后只计算两份有工程意义的真实完整带材姿态：`INBOARD_R15_ALPHA25_MID_SLACK` 的 STOW 与 DOCK q=4.013mm。每份都通过修复后的实际 `solid_intersection`，生成完整 per-cell 原始 signed volume 及上界记录；不为已否决的七族路线重复全量搜索。

原 23 个收据断言通过不表示在本轮重算了旧 63 个姿态或 6804 个 loft。两份新实际几何回执保留 B 舱碰撞，不证明真实 FPC、材料寿命、USB SI、电源安全、机械保护或 OLED 资格。`manufacturing_go=false`。
