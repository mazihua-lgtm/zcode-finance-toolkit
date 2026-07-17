---
name: codegraph
description: >
  项目代码知识图谱。当用户说"项目里有什么""有哪些函数""列出API接口""数据库表结构""找到认证代码"等探索性查询时触发。
  自动扫描项目，提取函数、类、API路由、数据库表，建立关系图谱，支持自然语言查询。
  支持 Python、JavaScript/TypeScript、SQL/Prisma。
---

# CodeGraph —— 项目代码知识图谱

把任何项目变成可查询的知识图谱。

## 功能

- 🔍 **自动扫描**：解析 Python/JS/TS/SQL 文件，提取函数、类、API 路由、DB 表
- 🗺️ **关系图谱**：构建文件依赖、模块导入关系
- 💬 **自然语言查询**：用中文直接问代码库

## 使用

```bash
# 扫描项目
python3 {baseDir}/scripts/codegraph.py scan

# 查看摘要
python3 {baseDir}/scripts/codegraph.py report

# 查询
python3 {baseDir}/scripts/codegraph.py query "有哪些API接口"
python3 {baseDir}/scripts/codegraph.py query "数据库表"
python3 {baseDir}/scripts/codegraph.py query "auth"
```

## 触发

- "项目里有什么"
- "列出所有函数"
- "有哪些API接口"
- "数据库表结构"
- "认证相关的代码在哪"
