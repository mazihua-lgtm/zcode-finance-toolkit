# 🧰 ZCode Finance Toolkit

> 一站式金融投研工具箱 —— 一个插件，三个技能，覆盖诊断、省钱、管理。

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![ZCode](https://img.shields.io/badge/ZCode-Plugin-6366f1)](https://zcode.ai)

---

## 安装

```bash
# 从 ZCode 插件市场搜索 "Finance Toolkit" 一键安装
# 或手动安装：
git clone https://github.com/mazihua-lgtm/zcode-finance-toolkit.git ~/.zcode/skills/finance-toolkit
```

## 包含技能

### 📊 ETF Diagnosis — 持仓诊断 + 机会发现

```
"分析我的ETF持仓" → 多维度诊断报告
"今天有什么机会"  → 全市场扫描
"调仓建议"       → 风险平价/最大夏普/最小方差多算法对比
```

### 💸 PromptPress — 中文 Prompt 压缩

```
"压缩一下" → 自动精简 prompt，平均省 26% token
```

### 📦 SkillVault — 技能管理器

```
"我安装了哪些技能" → 列出 42 个技能，分类展示
"搜索ETF技能"     → 关键词搜索
"安装一个技能"     → 从 GitHub 一键安装
```

## 自动化

- **SessionStart Hook**：开聊自动展示持仓摘要
- **预警系统**：溢价/回撤触发提醒

## 技术栈

- Python 3.9+
- 东方财富妙想 API
- ZCode Skill + Hook + Plugin 三件套

## 作者

独立开发者，专注金融数据 × AI 工具。欢迎 PR 和 Issue。

## License

MIT
