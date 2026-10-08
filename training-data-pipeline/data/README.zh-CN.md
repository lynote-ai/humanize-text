# Demo 数据

[英文版](README.md)

只有 `demos/` 子目录允许公开。它包含 5 个流水线阶段，每阶段严格 50 条 JSONL。`demos/manifest.yaml` 固定登记路径、条数、选取策略和 SHA-256。

如果记录包含 source 字段，`crawl` 表示公开的开源数据，`private` 表示公司的内部数据。内部数据集名称和来源特有标识不会公开。

## Schema

- `01_sft`：包含 `system`、`user`、`assistant` 三条消息的 SFT 记录。
- `02_reservation`：包含两条生成提示词、保留的 desirable response 和身份哈希。
- `03_generation`：包含输入身份、六条候选链及其生成元数据。
- `04_negative_selection`：包含三条消息和布尔类型 `label` 的 KTO 记录。
- `05_structure_refresh`：按照结构优先策略构建、包含三条消息和布尔类型 `label` 的 KTO 记录。

记录会保留最初随机分配到的 System Prompt。带固定种子的随机采样方法和 5 个代表性示例见 [Prompt 设计说明](../docs/PROMPTS.zh-CN.md)。

## 发布门禁

执行：

```bash
make demo-validate
```

如果阶段缺失、任一文件不是 50 条、文件变化后未更新 manifest 哈希、JSON 非法，或 `data/demos` 下出现额外 JSONL，校验都会失败。

推送到 GitHub 前，仍需人工复核全部 250 条 demo 的源数据许可证、个人或保密信息以及再分发权利。自动门禁只负责限制数量和检查完整性，不替代法律与隐私判断。
