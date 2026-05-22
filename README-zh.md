<p align="center">
  <img src="presentation/banner.png" alt="Humanize-Text" width="600"/>
</p>

<p align="center">
  <a href="https://github.com/lynote-ai/humanize-text/stargazers"><img src="https://img.shields.io/github/stars/lynote-ai/humanize-text?style=social" alt="Stars"></a>
  <a href="https://github.com/lynote-ai/humanize-text/network/members"><img src="https://img.shields.io/github/forks/lynote-ai/humanize-text?style=social" alt="Forks"></a>
  <a href="https://github.com/lynote-ai/humanize-text/blob/main/LICENSE"><img src="https://img.shields.io/github/license/lynote-ai/humanize-text" alt="License"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/python-3.10+-blue.svg" alt="Python"></a>
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/试用-Lynote.ai-brightgreen?style=for-the-badge" alt="Lynote.ai"></a>
</p>

<p align="center">
  <a href="README.md">English</a> | 中文
</p>

---

## Humanize-Text 是什么？

一个**可直接投产的** AI 文本拟人化工具，通过多语言翻译链将 AI 生成的文本改写为自然的人类写作风格。这是真正可运行的工作流，不是 Demo。

### v1.5 — Standard 管线

Standard 管线在保留原文风格的同时，通过 5 步多语言链路 + 关键步骤 LLM 拟人化改写来处理文本。

```
输入 (EN) → 中文 (LLM 改写) → 日语 (LLM 改写) → 德语 (谷歌翻译) → 西语 (小牛翻译) → 目标语言 (小牛翻译)
```

**特点：**
- 所有方案中原文风格保留度最好
- 处理速度快
- 关键信息保留率 100%（50 组文本对验证）
- 专家综合评分：9.1/10

> **想要更高绕过率 + 全方案融合？**
> [Lynote.ai](https://lynote.ai) 将 Standard + Advanced + Focus 三个管线融合为一个智能系统 — 自动为每段文本选择最优方案。
>
> **[免费试用 Lynote.ai →](https://lynote.ai)**

---

## 工作原理

### 逐步管线

| 步骤 | 引擎 | 转换方向 | 目的 |
|------|------|---------|------|
| 1 | DeepSeek (温度 1.3) | 输入 → 中文 | LLM 拟人化改写 + 语言转换 |
| 2 | DeepSeek (温度 1.3) | 中文 → 日语 | 二次 LLM 拟人化 + 远距离语种 |
| 3 | 谷歌翻译 | 日语 → 德语 | 机器翻译结构性扰动 |
| 4 | 小牛翻译 | 德语 → 西语 | 跨引擎分布偏移 |
| 5 | 小牛翻译 | 西语 → 目标语言 | 最终重构到目标语言 |

### 为什么这条链路有效

1. **步骤 1–2（LLM 改写）：** DeepSeek 在温度 1.3 下边翻译边改写，通过创造性变化打破 AI 统计指纹。每步携带上一轮的历史记录。
2. **步骤 3–5（多引擎翻译）：** 三个不同 NMT 引擎（谷歌 → 小牛 → 小牛）引入叠加的结构变化，任何单引擎指纹都无法存活。
3. **远距离语种：** 中文 → 日语 → 德语 → 西语，每一跳都最大化语言距离，确保彻底的结构重组。

---

## Lynote.ai — 超越 Standard

<p align="center">
  <a href="https://lynote.ai">
    <img src="presentation/lynote_banner.png" alt="Lynote.ai" width="500"/>
  </a>
</p>

上面的 Standard 管线是**三个层级之一**，各有不同的取舍：

| 层级 | 风格保留度 | 速度 | 方案 |
|------|-----------|------|------|
| **Standard**（本仓库） | 最好 | 快 | 翻译链 |
| **Advanced** | 良好 | 中等 | 翻译链 + LLM 多轮重写 |
| **Focus** | 一般 | 较慢 | 翻译链 + 检测引导反馈循环 |

**[Lynote.ai](https://lynote.ai)** 融合全部三个层级，自动为每段文本选择最优方案：

- **智能层级选择** — 分析文本，逐段选择 Standard、Advanced 或 Focus
- **自适应组合** — 可在同一文档内混合使用多个层级
- **支持 10+ 种语言** — 英语、中文、日语、韩语、西班牙语、法语、德语等
- **粘贴即用** — 无需部署，无需 API Key，无需配置

<p align="center">
  <a href="https://lynote.ai"><img src="https://img.shields.io/badge/免费试用_Lynote.ai-brightgreen?style=for-the-badge" alt="免费试用 Lynote.ai"></a>
</p>

---

## 快速开始

| 方式 | 适合人群 | 操作 |
|------|---------|------|
| [Lynote.ai](https://lynote.ai) | 所有人 — 全层级，零部署 | 访问 [lynote.ai](https://lynote.ai) |
| n8n 工作流 | 无代码自动化用户 | 导入 [`n8n/humanize_standard.json`](n8n/humanize_standard.json) |
| Python 脚本 | 开发者 | 见下方 |

### Python

```bash
git clone https://github.com/lynote-ai/humanize-text.git
cd humanize-text
pip install -r requirements.txt
cp config/config.example.toml config/config.toml
# 在 config.toml 中填入 API 密钥
python -m src.pipeline --input "你的 AI 生成文本"
```

### n8n 工作流

1. 将 `n8n/humanize_standard.json` 导入你的 n8n 实例
2. 在 HTTP Request 节点中配置 DeepSeek API Key
3. 运行 — 输入文本，输出拟人化结果

---

## 质量指标

在 50 组文本对上经专家评估：

| 维度 | 评分（满分 10 分） |
|------|-------------------|
| 信息完整性 | 10.0 |
| 语言流畅度 | 9.0 |
| 风格适应性 | 8.8 |
| 可读性 | 9.2 |
| 创意与感染力 | 8.5 |
| **综合评分** | **9.1** |

- **关键信息保留率：** 100%（50/50 组）
- 所有文本均完整保留原文关键信息，无重大遗漏或意义扭曲

---

## 文档

- [管线技术详解](docs/pipeline.md)
- [配置指南](docs/configuration.md)
- [n8n 工作流指南](docs/n8n-guide.md)
- [常见问题](docs/faq.md)

---

## 开源协议

MIT License。详情见 [LICENSE](LICENSE)。

---

## 相关链接

- [Lynote.ai — AI 拟人化平台](https://lynote.ai)
- [报告 Bug](https://github.com/lynote-ai/humanize-text/issues)

### 推荐项目

- [MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) — AI 短视频生成器
- [AiToEarn](https://github.com/yikart/AiToEarn) — AI 内容发布工具

---

## Star 趋势

<p align="center">
  <a href="https://star-history.com/#lynote-ai/humanize-text&Date">
    <img src="https://api.star-history.com/svg?repos=lynote-ai/humanize-text&type=Date" alt="Star History Chart" width="500">
  </a>
</p>

---

<p align="center">
  <b>如果这个项目对你有帮助，请给一个 ⭐！</b>
</p>
