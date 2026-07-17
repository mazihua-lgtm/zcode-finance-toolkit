---
name: posterpro
description: >
  公众号贴图内容工厂。当用户说"生成公众号封面""公众号选题""贴图内容""帮我做一个公众号封面"时触发。
  提供5大赛道30+选题，一键生成封面图和文案。快速测试公众号贴图方向。
---

# PosterPro —— 公众号贴图内容工厂

## 功能

- 🎨 一键生成公众号封面图（900x383，大字+痛点关键词）
- 📚 5大赛道 30+ 选题库（职场/女性/副业/亲子/养生）
- ✍️ 自动生成贴图文案

## 使用

```bash
# 列出所有赛道
python3 {baseDir}/scripts/posterpro.py list

# 查看职场选题
python3 {baseDir}/scripts/posterpro.py topics 职场

# 生成封面
python3 {baseDir}/scripts/posterpro.py cover 新人入职前30天最该做的5件事

# 一键生成完整内容
python3 {baseDir}/scripts/posterpro.py make 搞钱副业 0
```

## 依赖

```bash
pip3 install Pillow
```
