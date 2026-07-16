---
name: promptpress
description: >
  中文 Prompt 压缩器。当用户说"压缩一下""省点 token""prompt 太长了""帮我缩短这段话"等表达时触发。
  自动将冗长的中文 prompt 压缩为简洁版本，平均节省 25%+ token，相当于每月省四分之一的 AI 费用。
  也适用于用户说"精简""缩短""token too much""tokens太多了"等场景。
  不适用于代码压缩、英文翻译、内容改写等非压缩场景。
---

# PromptPress —— 中文 Prompt 压缩器

自动压缩中文 prompt，节省 25%+ token 消耗。

## 功能

- 去除礼貌冗余（请问、麻烦你、谢谢...）
- 删除虚词/量词/语气词（的、了、吗、个...）
- 技术术语中→英（数据库→DB，人工智能→AI）
- 常用短语符号化（查询→@，生成→→）

## 使用方式

### 自然语言触发

直接说：
- "压缩一下"
- "帮我把这段 prompt 精简"
- "省点 token"
- "太长了，缩短一下"

Skill 会自动取**上一条用户消息**进行压缩。

### 命令行

```bash
python3 {baseDir}/scripts/compress.py "你的 prompt"
# 或管道输入
echo "你的 prompt" | python3 {baseDir}/scripts/compress.py
```

### 查看效果

```bash
python3 {baseDir}/scripts/compress.py bench
```

## 压缩效果

| 场景 | 原始 | 压缩后 | 压缩率 |
|------|:--:|:--:|:--:|
| 日常提问 | 51字 | 27字 | **47%** |
| 编程任务 | 77字 | 53字 | **31%** |
| 数据分析 | 71字 | 38字 | **47%** |
| 持仓诊断 | 182字 | 145字 | **20%** |
| **平均** | — | — | **26%** |

## 原理

纯规则引擎，零 API 消耗。不调用任何 AI 模型，即时响应。
