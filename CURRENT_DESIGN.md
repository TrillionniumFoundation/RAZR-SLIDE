# 当前研究设计｜KEY通道与外盖绕接

独立GitHub检出复核：源码 `1d278a6f55995b90609856c7817477a632e3b919` 的12项新候选测试、130对完整运动及材料/42个未改零件/92个装配实体复验通过，源字节和工作树未变。完整369项在提交前同字节源码上执行，本次独立检出未重复全部369项。回执：`engineering/keycover-geometry-20261014/fresh-GitHub-verification/SUMMARY.json`。外盖实际装入仍不合格。

当前源码：`integration/keycover_bypass.py`。
当前证据：`engineering/keycover-geometry-20261014/SUMMARY.json` 及同目录README。

## 已验证范围

STOW q=0–12mm、此前下向恢复力假设下，130对完整运动检查零正干涉，独立76份STEP复读一致。369项/21组测试通过；原564/184采样和64阶段/506静态检查通过。完整装配92个实体及42个非改动零件逐一比对。

## 必须保留的边界

只改外盖和外根座。外盖q下界1.7→-0.4mm，局部装配外包络不增；不代表实际手机内腔已通过。原底板和孔位保留，完整两片重新连接，不丢弃材料碎片。

盖件实际装入尚未闭合：根座先闭合后，上方装入在r=+0.05mm仍有实际碰撞；原件同样失败。原184/64项不覆盖这一步，不能替代新增装配拒绝。

## 下一步

先验证外盖进入、根座闭合及紧固的真实装配顺序和夹具/工具通道；再做载荷、公差与实物资格。同版本手机内腔、完整布线端接、指定OLED/FPC、独立B电池和USB/OLED系统仍未闭合。

所有candidate/fixture/manufacturing放行继续为false。未上电、未采购、未合并主干。

## 历史证据

连续接触及四项KEY旧失败：`engineering/contact-motion-20261014/`。
上一版装入与根座局部结果：`engineering/stow-installation-closure-20261014/`。
恢复工具/统一测试入口与原18项失败：`engineering/workplan-execution-20261014/`。
