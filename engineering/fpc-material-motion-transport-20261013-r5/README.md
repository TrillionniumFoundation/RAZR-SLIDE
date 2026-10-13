# R5 失败材料场：无损传输归档

原投影截面场的 12,857,743 字节 NPZ 保持原样，未删除或改写。GitHub 连接器本次 blob 提交返回非 JSON 工具错误，根未创建该组 commit。为了完成可复核推送，将这一个原文件分成固定字节块提交；没有改变任何材料数值、NaN、ZIP 成员或失败结论。

`parts_manifest.json` 保留原始相对路径/大小/SHA256及所有块的大小/SHA256。仓库中这个 NPZ 以归档块表示，其余冻结 R5 文件仍逐字节直接存储。恢复后可与原 R5 `file_manifest.json` 核对：

```sh
python3 engineering/fpc-material-motion-transport-20261013-r5/restore_history.py
```

工具验证每块及完整原始 SHA，已有相同文件只核对，已有不同文件拒绝覆盖。根在独立临时目标实际恢复并核对原始字节通过；回执见 `restore_verification.json`。原始本地 NPZ及冻结源/回执不改；本变更仅为传输归档，不是新物理资格。`manufacturing_go=false`。
