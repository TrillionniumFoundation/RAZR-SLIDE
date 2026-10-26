# GitHub Actions 启动前失败：最小管理员交接

目标运行：[39907440200](https://github.com/TrillionniumFoundation/RAZR-SLIDE/actions/runs/39907440200)，attempt 1，源码 `e76ff339cbd38610b42f550d1d990131233c8f7d`。

已验证 16 个 job records 中有 15 个 failure、1 个 skipped。所有失败 job 均为 `runner_id=0`、`steps=[]`；实际执行 0，artifact 0。GitHub API 的实际 conclusion 值为 `failure`；“启动前失败”描述来自未分配 runner、未执行 step 的观察，具体原因仍未知。

## 只需提供两条原始 annotation

| 优先级 | Job / runner label | Check ID | 原始 annotations API |
| --- | --- | --- | --- |
| 1 | plan-current-unit-suites / ubuntu-slim | `120262641636` | [GET annotations](https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/120262641636/annotations) |
| 2 | native-product-ep5 / ubuntu-24.04 | `120262641313` | [GET annotations](https://api.github.com/repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/120262641313/annotations) |

请提供以上两个 API 返回的完整 annotation 数组，保留 `title`、`message`、`raw_details`、`annotation_level`，并注明对应 check ID。若使用 GitHub 页面，复制这两项相同 annotation 的原文即可。每项已观察到 `annotations_count=1`；当前连接器拒绝读取正文，commit check 输出中的 title/summary/text 均为空。

可由有权读取该仓库检查结果的管理员执行：

```bash
gh api repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/120262641636/annotations > annotation-120262641636.json
gh api repos/TrillionniumFoundation/RAZR-SLIDE/check-runs/120262641313/annotations > annotation-120262641313.json
```

完整 15 个失败 check 的 ID、名称和 API 路径见同目录 `hosted-admin-handoff.json`。先取得原始失败正文，再决定是否需要查询具体组织/仓库策略或 runner 配置。

## 已完成的排查

当前 workflow 引用的四个固定 action SHA 均能在其声明的上游仓库解析为真实 commit；证据为 `pinned-actions-resolution.json`。因此可排除“引用了不存在的 action commit”，但这不能证明 runner 策略、运行时兼容性或启动失败原因。尚未取得任何可确认账单原因的原始诊断。

本交接只请求读取失败证据；没有发起重跑，也没有更改 Actions、runner 或费用设置。本地严格锁环境的测试/native 执行回执保持独立身份，不能替代 hosted runner 已启动的证据。
