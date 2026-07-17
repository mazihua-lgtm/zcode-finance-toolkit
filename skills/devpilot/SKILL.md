---
name: devpilot
description: >
  个人开发助手，聚合所有 ZCode 工具数据提供统一仪表盘。
  当用户说"仪表盘""开发环境概览""我的项目整体情况""环境健康检查""今天有什么需要关注的"时触发。
  自动汇总投资组合、代码库、AI费用、安全快照、技能配置等所有工具的最新数据。
---

# DevPilot —— 个人开发助手

一个入口，聚合所有数据。

## 功能

- 🏠 **仪表盘**：投资 + 代码 + 费用 + 安全 + 工具链，一张图看完
- 🔍 **健康检查**：自动发现潜在问题（未扫描/费用超标/安全缺失）
- 📊 **数据聚合**：读取 Portfolio + CodeGraph + TokenTrack + ChangeGuard + SkillVault 所有数据

## 使用

```bash
# 仪表盘
python3 {baseDir}/scripts/devpilot.py dashboard

# 健康检查
python3 {baseDir}/scripts/devpilot.py check
```

## 依赖

自动读取以下工具的数据（无需额外配置）：
- Portfolio（持仓）
- CodeGraph（代码库）
- TokenTrack（费用）
- ChangeGuard（安全）
- SkillVault（技能统计）
