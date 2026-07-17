"""
PosterPro —— 公众号贴图内容工厂
封面生成 + 选题库 + 文案模板
"""

import json
import os
import textwrap
from pathlib import Path
from datetime import datetime

try:
    from PIL import Image, ImageDraw, ImageFont
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

OUTPUT_DIR = Path.home() / "Desktop" / "posterpro"
TOPIC_FILE = Path(__file__).parent / "topics.json"


# ═══════════════════════════════════════════════
#  选题库
# ═══════════════════════════════════════════════

DEFAULT_TOPICS = {
    "职场": {
        "人群": "职场新人/转行者",
        "风格": "干货+避坑",
        "选题": [
            {"title": "新人入职前30天最该做的5件事", "hook": "90%的人前3个月踩的坑都在这里了"},
            {"title": "职场里最吃亏的3种说话方式", "hook": "看看你中了几个"},
            {"title": "领导说'辛苦了'，聪明人从不回'不辛苦'", "hook": "换个说法，领导对你刮目相看"},
            {"title": "入职3个月没转正的人，都输在了这一点", "hook": "不是能力问题，是信息差"},
            {"title": "月薪3千和月薪3万的人，差的从来不是能力", "hook": "把这5个习惯刻进脑子里"},
        ],
        "模板": "📌 {title}\n\n{hook}\n\n---\n{body}\n\n💬 你遇到过这种情况吗？评论区聊聊"
    },
    "女性成长": {
        "人群": "25-35岁女性",
        "风格": "治愈+独立",
        "选题": [
            {"title": "高情商的女人，从不在这3件事上浪费时间", "hook": "30岁以后才发现，这些都是消耗品"},
            {"title": "一个女生开始变强的5个信号", "hook": "第3个很多人做不到"},
            {"title": "真正聪明的女人，都学会了'不解释'", "hook": "你的时间很贵，别浪费在解释上"},
            {"title": "工资5000到月入5万，她只用了1年", "hook": "不是运气，是换了3种思维"},
            {"title": "那些后来过得好的女生，都有这个习惯", "hook": "每天10分钟，改变正在发生"},
        ],
        "模板": "💜 {title}\n\n{hook}\n\n---\n{body}\n\n💬 你觉得自己在哪一步？"
    },
    "搞钱副业": {
        "人群": "想增加收入的上班族",
        "风格": "实用+清单",
        "选题": [
            {"title": "下班后能做的5种副业，月入3000起步", "hook": "不用露脸不用拍视频"},
            {"title": "2026年普通人最容易上手的3个赚钱方向", "hook": "门槛低，适合新手"},
            {"title": "工资外的第一桶金，80%的人都是这样赚到的", "hook": "找对方法比拼命更重要"},
            {"title": "副业做了3个月，我总结了5个血泪教训", "hook": "第4个很多人都踩过"},
            {"title": "一个人一台电脑，这个冷门赛道月入过万", "hook": "知道的人还不多"},
        ],
        "模板": "💰 {title}\n\n{hook}\n\n---\n{body}\n\n💬 你做过副业吗？效果怎么样？"
    },
    "家庭亲子": {
        "人群": "宝妈/家长",
        "风格": "温暖+实操",
        "选题": [
            {"title": "挑食宝宝爱吃的5道营养辅食", "hook": "我家娃连碗底都舔干净了"},
            {"title": "辅导作业不吼不叫，这3个方法真管用", "hook": "试了一个月，全家都轻松了"},
            {"title": "孩子被欺负，别再说'打回去'了", "hook": "聪明妈妈都这样做"},
            {"title": "0-3岁早教不用报班，每天15分钟就够了", "hook": "把这5个游戏收藏起来"},
            {"title": "婆婆带娃和自己带娃，差别到底在哪", "hook": "不是爱不爱的问题"},
        ],
        "模板": "👶 {title}\n\n{hook}\n\n---\n{body}\n\n💬 你家宝宝挑食吗？"
    },
    "健康养生": {
        "人群": "中老年/亚健康人群",
        "风格": "通俗+科学",
        "选题": [
            {"title": "中老年人能看懂的5个日常健康习惯", "hook": "不花钱，坚持就有效果"},
            {"title": "晚上睡不好？试试这3个方法", "hook": "很多人都不知道"},
            {"title": "天天吃降压药，这4件事一定要知道", "hook": "医生不会主动告诉你"},
            {"title": "50岁后，比运动更重要的3件事", "hook": "很多人在第一条就错了"},
            {"title": "身体有这些信号，说明你该休息了", "hook": "别等生病了才后悔"},
        ],
        "模板": "🏥 {title}\n\n{hook}\n\n---\n{body}\n\n💬 转发给关心的人~"
    },
}


def generate_topic(niche: str = "职场", index: int = 0) -> dict:
    """获取一个选题。"""
    topics = DEFAULT_TOPICS.get(niche, DEFAULT_TOPICS["职场"])
    selection = topics["选题"][index % len(topics["选题"])]
    return {
        "niche": niche,
        "style": topics["风格"],
        "audience": topics["人群"],
        "title": selection["title"],
        "hook": selection["hook"],
        "template": topics["模板"],
    }


def list_niches() -> str:
    """列出所有可用赛道。"""
    lines = ["## 🎯 可用赛道", ""]
    for name, info in DEFAULT_TOPICS.items():
        lines.append(f"- **{name}**：{info['人群']} | {info['风格']}")
    return "\n".join(lines)


def list_topics(niche: str = "职场") -> str:
    """列出某赛道的所有选题。"""
    topics = DEFAULT_TOPICS.get(niche, DEFAULT_TOPICS["职场"])
    lines = [f"## {niche} 赛道选题", ""]
    for i, t in enumerate(topics["选题"]):
        lines.append(f"{i+1}. **{t['title']}** — {t['hook']}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  封面生成
# ═══════════════════════════════════════════════

def generate_cover(title: str, niche: str = "", output_path: str = "") -> str:
    """生成公众号贴图封面。"""
    if not HAS_PIL:
        return "❌ Pillow 未安装。请运行: pip3 install Pillow"

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 公众号封面尺寸 900x383
    W, H = 900, 383
    img = Image.new("RGB", (W, H), color=_bg_color(niche))
    draw = ImageDraw.Draw(img)

    # 加载字体
    title_font = _load_font(32, bold=True)
    tag_font = _load_font(18)

    # 左上角标签
    tag_text = f"#{niche}" if niche else "#公众号"
    draw.text((30, 20), tag_text, fill="#ffffff80", font=tag_font)

    # 标题文字（居中偏左）
    wrapped = textwrap.fill(title, width=18)
    y = 100
    for line in wrapped.split("\n"):
        bbox = draw.textbbox((0, 0), line, font=title_font)
        w = bbox[2] - bbox[0]
        x = 60
        # 白色文字 + 黑色阴影效果
        draw.text((x + 2, y + 2), line, fill="#000000", font=title_font)
        draw.text((x, y), line, fill="#ffffff", font=title_font)
        y += bbox[3] - bbox[1] + 10

    # 底部装饰线
    draw.rectangle([60, H - 40, 200, H - 37], fill="#ffffff60")

    output = output_path or str(OUTPUT_DIR / f"cover_{datetime.now().strftime('%H%M%S')}.png")
    img.save(output)
    return f"✅ 封面已生成: {output}"


def _bg_color(niche: str) -> tuple:
    colors = {
        "职场": (41, 65, 128), "女性成长": (128, 41, 105),
        "搞钱副业": (180, 100, 20), "家庭亲子": (41, 128, 100),
        "健康养生": (41, 100, 80),
    }
    return colors.get(niche, (60, 60, 80))


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """加载字体，macOS 优先使用系统字体。"""
    fonts = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
    ]
    for f in fonts:
        if os.path.exists(f):
            return ImageFont.truetype(f, size)
    return ImageFont.load_default()


# ═══════════════════════════════════════════════
#  一键生成完整内容
# ═══════════════════════════════════════════════

def generate_full(niche: str = "职场", index: int = 0, body: str = "") -> str:
    """一键生成：封面 + 文案。"""
    topic = generate_topic(niche, index)
    cover_path = generate_cover(topic["title"], niche)
    body_text = body or f"暂无详细正文，请根据选题自行补充。\n\n建议包含：一个真实案例 + 3-5个具体方法 + 一个互动问题。"
    full_text = topic["template"].format(
        title=topic["title"],
        hook=topic["hook"],
        body=body_text,
    )
    return (
        f"## 📱 内容已生成\n\n"
        f"**赛道**：{niche} ｜ **风格**：{topic['style']}\n\n"
        f"{cover_path}\n\n"
        f"### 📝 文案\n\n{full_text}"
    )


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "list":
        print(list_niches())

    elif cmd == "topics" and len(sys.argv) > 2:
        print(list_topics(sys.argv[2]))

    elif cmd == "cover" and len(sys.argv) > 2:
        title = " ".join(sys.argv[2:])
        print(generate_cover(title))

    elif cmd == "make" and len(sys.argv) > 2:
        niche = sys.argv[2]
        idx = int(sys.argv[3]) if len(sys.argv) > 3 else 0
        body = sys.argv[4] if len(sys.argv) > 4 else ""
        print(generate_full(niche, idx, body))

    else:
        print("PosterPro —— 公众号贴图内容工厂")
        print()
        print("用法:")
        print("  posterpro list                     列出所有赛道")
        print("  posterpro topics <赛道>            列出赛道选题")
        print("  posterpro cover <标题>             生成封面图片")
        print("  posterpro make <赛道> [序号]      一键生成完整内容")
        print()
        print("示例:")
        print("  posterpro list")
        print("  posterpro topics 职场")
        print("  posterpro cover 新人入职前30天最该做的5件事")
        print("  posterpro make 搞钱副业 0")


if __name__ == "__main__":
    main()
