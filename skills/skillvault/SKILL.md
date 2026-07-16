---
name: skillvault
description: >
  ZCode 技能注册表。当用户说"我安装了哪些技能""搜索技能""有什么好用的技能""技能统计""安装一个技能"时触发。
  支持：列出所有已安装技能、按关键词搜索、分类统计、从 GitHub 一键安装新技能。
  该技能本身也可用于发现和管理其他 ZCode 技能。
---

# SkillVault —— ZCode 技能注册表

扫描、搜索、管理你的所有 ZCode 技能。

## 命令

| 命令 | 功能 |
|------|------|
| `python3 {baseDir}/scripts/skillvault.py list` | 列出所有已安装技能 |
| `python3 {baseDir}/scripts/skillvault.py search <关键词>` | 搜索技能 |
| `python3 {baseDir}/scripts/skillvault.py stats` | 分类统计 |
| `python3 {baseDir}/scripts/skillvault.py install <github-url>` | 从 GitHub 安装 |

## 触发

- "我安装了哪些技能"
- "搜索 ETF 相关的技能"
- "有没有好用的金融技能"
- "技能统计"
- "安装一个 xxx 技能"

## 统计

当前扫描：42 个技能，其中 18 个含可执行脚本。
