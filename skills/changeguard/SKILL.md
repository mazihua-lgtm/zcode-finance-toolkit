---
name: changeguard
description: >
  AI 变更追踪与安全审查。当用户说"审查变更""检查一下改了哪些文件""有没有安全风险""AI改了什么"时触发。
  自动对比代码快照，检测文件变更、密钥泄露、敏感配置修改。
  适用于 AI Agent 修改代码后的安全检查场景，也适用于日常代码审查。
---

# ChangeGuard —— AI 变更审查

SessionStart 自动快照 → 随时检查变更 → 标记风险。

## 功能

- 📸 **自动快照**：会话开始时记录所有文件哈希
- 🔍 **变更检测**：对比快照，找出新增/删除/修改的文件
- ⚠️ **风险扫描**：检测密钥泄露、大文件删除、敏感配置变更
- 📋 **审查报告**：一键生成 Markdown 审查清单

## 使用

```bash
# 创建快照
python3 {baseDir}/scripts/changeguard.py snapshot

# 检查变更
python3 {baseDir}/scripts/changeguard.py check

# 生成报告
python3 {baseDir}/scripts/changeguard.py report
```

## 触发

- "审查一下变更"
- "AI 改了什么"
- "检查有没有安全问题"
- "看看代码有没有泄露密钥"
