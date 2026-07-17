---
name: publishpro
description: >
  多平台内容发布引擎。当用户说"发布到多个平台""多平台发布""生成公众号和小红书内容"时触发。
  配合 PosterPro 使用，将内容自动适配为公众号/小红书/Twitter 的专属格式。
  一键输出三个平台的发布文件。
---

# PublishPro —— 多平台发布引擎

PosterPro 出选题 → PublishPro 出格式

## 功能

- 📱 **公众号格式**：封面+标题+正文+互动引导
- 📕 **小红书格式**：短标题+话题标签+短文案
- 🐦 **Twitter 格式**：280字线程自动分段+编号

## 使用

```bash
python3 {baseDir}/scripts/publishpro.py "标题" "正文内容" 赛道 封面路径 链接
```

## 配合 PosterPro

```bash
# 1. PosterPro 生成封面
python3 posterpro.py make 搞钱副业 0

# 2. PublishPro 生成多平台内容
python3 publishpro.py "标题" "正文" 搞钱副业 ~/Desktop/posterpro/cover_*.png
```
