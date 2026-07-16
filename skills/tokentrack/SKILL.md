---
name: tokentrack
description: >
  AI 费用追踪器。当用户说"花了多少钱""token费用""AI账单""费用报告""这个月烧了多少"时触发。
  自动记录每次会话的 token 消耗和费用，支持日报/周报/月报，按项目分类统计。
  与 PromptPress 配合使用：一个省钱，一个看钱。
---

# TokenTrack —— AI 费用追踪

自动记录 + 智能估算 + 可视化报告。

## 功能

- 📊 自动记录每次会话
- 💰 实时估算 token 费用（支持 DeepSeek/Claude 等多种模型定价）
- 📂 按项目分类统计
- 📅 日报/周报/月报
- 🔮 预估月度费用

## 使用

```bash
# 查看近30天报告
python3 {baseDir}/scripts/tokentrack.py report

# 查看近7天
python3 {baseDir}/scripts/tokentrack.py report 7

# 查看近90天
python3 {baseDir}/scripts/tokentrack.py report 90
```

## 触发

- "这个月花了多少 token"
- "AI 账单"
- "费用报告"
- "看看烧了多少钱"
