"""
PublishPro —— 多平台内容发布引擎
PosterPro 输出 → 自动适配公众号/小红书/Twitter 格式
"""

import json
import shutil
from datetime import datetime
from pathlib import Path

OUTPUT_DIR = Path.home() / "Desktop" / "publishpro"

# ═══════════════════════════════════════════════
#  格式适配
# ═══════════════════════════════════════════════

def for_wechat(title: str, body: str, cover_path: str = "") -> dict:
    """生成公众号格式。"""
    # 公众号：封面图 + 标题 + 正文（支持长文）
    formatted = (
        f"# {title}\n\n"
        f"{body}\n\n"
        f"---\n"
        f"💬 欢迎在评论区留言讨论\n"
        f"📌 觉得有用请点赞+在看，让更多人看到"
    )
    return {
        "platform": "公众号",
        "title": title,
        "cover": cover_path,
        "content": formatted,
        "file": _save("wechat", title, formatted),
    }


def for_xiaohongshu(title: str, body: str, niche: str = "", cover_path: str = "") -> dict:
    """生成小红书格式。"""
    # 小红书：短标题 + 标签 + 短文案 + 话题标签
    tags = _gen_tags(niche)
    short_body = body[:300] + "..." if len(body) > 300 else body
    formatted = (
        f"{title}\n\n"
        f"{short_body}\n\n"
        f"{tags}"
    )
    return {
        "platform": "小红书",
        "title": title,
        "cover": cover_path,
        "content": formatted,
        "file": _save("xiaohongshu", title, formatted),
    }


def for_twitter(title: str, body: str, link: str = "", niche: str = "") -> str:
    """生成 Twitter/X 线程格式。"""
    # Twitter：每条 280 字符，自动分段 + 编号 + hashtags
    tags = _gen_tags(niche, prefix="#")
    lines = body.split("\n")
    tweets = []
    current = f"🧵 {title}\n\n"

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if len(current) + len(line) + 1 > 270:
            tweets.append(current.strip())
            current = ""
        current += line + "\n"

    if current.strip():
        tweets.append(current.strip())

    # 最后一条加链接
    if tweets and link:
        tweets[-1] += f"\n\n{link}"

    # 加标签
    if tags and tweets:
        tweets[-1] += f"\n\n{tags}"

    formatted = "\n\n---\n\n".join(tweets)
    return {
        "platform": "Twitter/X",
        "title": title,
        "content": formatted,
        "thread_count": len(tweets),
        "file": _save("twitter", title, formatted),
    }


def publish_all(title: str, body: str, niche: str = "", cover_path: str = "", link: str = "") -> dict:
    """一键生成所有平台的发布内容。"""
    results = {
        "wechat": for_wechat(title, body, cover_path),
        "xiaohongshu": for_xiaohongshu(title, body, niche, cover_path),
        "twitter": for_twitter(title, body, link, niche),
    }
    # 生成汇总文件
    summary = _build_summary(title, niche, results)
    return {"results": results, "summary": summary, "dir": str(OUTPUT_DIR)}


# ═══════════════════════════════════════════════
#  辅助
# ═══════════════════════════════════════════════

def _gen_tags(niche: str, prefix: str = "#") -> str:
    tag_map = {
        "职场": ["职场干货", "职场新人", "升职加薪", "沟通技巧"],
        "女性成长": ["女性成长", "独立女性", "自我提升", "情感"],
        "搞钱副业": ["搞钱", "副业", "赚钱", "自由职业"],
        "家庭亲子": ["育儿", "宝妈", "亲子", "辅食"],
        "健康养生": ["健康养生", "养生", "中老年健康", "睡眠"],
    }
    tags = tag_map.get(niche, [niche])
    return " ".join(f"{prefix}{t}" for t in tags)


def _save(platform: str, title: str, content: str) -> str:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    safe = "".join(c for c in title[:30] if c.isalnum() or c in " _-")
    fname = f"{platform}_{safe}_{datetime.now().strftime('%H%M')}.txt"
    path = OUTPUT_DIR / fname
    path.write_text(content, encoding="utf-8")
    return str(path)


def _build_summary(title: str, niche: str, results: dict) -> str:
    lines = [
        f"# 📤 多平台发布包",
        f"",
        f"**选题**：{title}",
        f"**赛道**：{niche}",
        f"**生成时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"",
        f"## 📁 文件清单",
        f"",
    ]
    for key, r in results.items():
        lines.append(f"- **{r['platform']}**：`{r['file']}`" + (f"（{r.get('thread_count','')}条推文）" if key == "twitter" else ""))
    lines.append("")
    lines.append("---")
    lines.append("💡 封面图片请用 PosterPro 生成，然后手动上传到各平台。")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    if len(sys.argv) < 3:
        print("PublishPro —— 多平台内容发布引擎")
        print()
        print("用法:")
        print("  publishpro <标题> <正文> [赛道] [封面路径] [链接]")
        print()
        print("示例:")
        print('  publishpro "副业指南" "内容正文..." 搞钱副业 cover.png "https://..."')
        return

    title = sys.argv[1]
    body = sys.argv[2]
    niche = sys.argv[3] if len(sys.argv) > 3 else ""
    cover = sys.argv[4] if len(sys.argv) > 4 else ""
    link = sys.argv[5] if len(sys.argv) > 5 else ""

    result = publish_all(title, body, niche, cover, link)
    print(result["summary"])
    for key, r in result["results"].items():
        print(f"\n{'='*40}")
        print(f"📱 {r['platform']}")
        print(f"{'='*40}")
        print(r["content"][:500])


if __name__ == "__main__":
    main()
