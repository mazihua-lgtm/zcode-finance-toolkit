"""
PromptPress v2 —— 激进中文压缩引擎

策略（Caveman 中文版）：
  A. 删除所有语气词、虚词、量词、连词
  B. 保留：名词、动词、数字、关键形容词
  C. 符号化：用 → → 等符号替代常见模式
  D. 中英混合：技术术语用英文缩写
"""

import re


# A. 删除列表：虚词、量词、语气词
DROP_WORDS = [
    # 语气词
    "请问", "麻烦", "拜托", "谢谢", "感谢", "不好意思", "打扰",
    # 虚词
    "的", "地", "得", "了", "着", "过",
    "吗", "呢", "吧", "啊", "呀", "哦", "哈", "啦",
    "是", "很", "都", "也", "就", "才", "还", "又", "再",
    # 量词
    "一个", "一只", "一条", "一张", "一份", "一次", "一下", "一些",
    "这个", "那个", "这些", "那些", "哪个", "哪些",
    "什么", "怎么", "怎么样", "为什么",
    # 连词/过渡
    "然后", "而且", "但是", "不过", "所以", "因为", "如果", "虽然",
    "另外", "还有", "以及", "或者", "并且",
    # 冗余动词
    "进行", "做出", "给予", "加以", "予以", "实现",
    # 填充
    "可以", "能够", "需要", "应该", "必须",
    "我想", "我觉得", "我认为", "我希望", "我打算",
    "帮我", "帮我做", "帮我写", "帮我看", "帮我查",
    "能不能", "可不可以", "要不要",
]

# B. 短语 → 符号/缩写
SHORTCUT_MAP = {
    # 写/生成 → →
    "写一个": "→", "写一段": "→", "生成一个": "→", "创建": "→",
    "帮我写": "→", "帮我生成": "→",
    # 查/搜 → @
    "查询": "@", "搜索": "@", "查找": "@", "查看": "@",
    "帮我查": "@", "帮我搜索": "@",
    # 分析
    "帮我分析": "分析", "分析一下": "分析",
    # 输出
    "保存到": "→", "输出到": "→", "导出到": "→",
    # 常见后缀
    "ETF数据": "ETF", "股票数据": "股票",
    "实时行情": "行情",
    "帮我看看": "查看",
    "代码": "",
    "脚本": "",
    "函数": "func",
}

# C. 技术术语 → 英文缩写
TECH_TERMS = {
    "数据库": "DB", "人工智能": "AI", "机器学习": "ML",
    "应用程序接口": "API", "前端": "FE", "后端": "BE",
    "命令行": "CLI", "用户界面": "UI", "自然语言处理": "NLP",
    "软件开发工具包": "SDK", "搜索引擎优化": "SEO",
    "面向对象": "OOP", "函数式": "FP", "版本控制": "VCS",
    "内容分发网络": "CDN", "高可用": "HA", "负载均衡": "LB",
    "正则表达式": "regex", "回调函数": "callback",
}


def compress(text: str, level: str = "max") -> str:
    """
    压缩中文 prompt。
    level: "light" (保守) | "max" (激进，默认)
    """
    if level == "light":
        # 轻量模式：只删礼貌用语和常见冗余
        for word in ["请问", "麻烦你", "能不能帮我", "可不可以", "谢谢你", "不好意思", "打扰了"]:
            text = text.replace(word, "")
        text = re.sub(r"[的得了着过]", "", text)
        text = re.sub(r"\s{2,}", " ", text)
        return text.strip()

    # ---- max 模式 ----

    # 1. 删除虚词列表
    for word in DROP_WORDS:
        text = text.replace(word, "")

    # 2. 短语 → 符号
    for phrase, symbol in SHORTCUT_MAP.items():
        text = text.replace(phrase, symbol)

    # 3. 技术术语 → 英文
    for cn, en in TECH_TERMS.items():
        text = text.replace(cn, en)
        # 也替换缩写+中文组合
        text = re.sub(rf"{en}[的]", en, text)

    # 4. 删除多余的"的"残留
    text = re.sub(r"(?<!\w)的(?!\w)", "", text)

    # 5. 清理标点
    text = re.sub(r"[，,]{2,}", "，", text)
    text = re.sub(r"[。.]{2,}", "。", text)
    text = re.sub(r"[！!]+", "!", text)
    text = re.sub(r"[？?]+", "?", text)
    text = re.sub(r"[；;]", "；", text)

    # 6. 清理空白
    text = re.sub(r"\s{2,}", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)

    # 7. 去除首尾标点残留
    text = re.sub(r"^[，,。.；;！!？?\s]+", "", text)
    text = re.sub(r"[，,。.；;！!？?\s]+$", "", text)

    return text.strip()


def ratio(original: str, compressed: str) -> float:
    """计算压缩率。"""
    if not original:
        return 0
    return round((1 - len(compressed) / len(original)) * 100, 1)


# ═══════════════════════════════════════════════
#  测试
# ═══════════════════════════════════════════════

TEST_CASES = [
    ("日常提问",
     "请问一下，麻烦你能不能帮我看看最近有什么好的ETF投资机会？我想了解一下半导体和新能源方面的，谢谢你！"),

    ("编程任务",
     "你好，我想请你帮我写一个Python脚本，这个脚本的功能是自动从东方财富网站上爬取A股所有ETF的实时行情数据，然后把数据保存到CSV文件里面，非常感谢！"),

    ("数据分析",
     "不好意思打扰了，我现在需要你做一件事情：帮我分析一下这份数据，看看里面有没有什么异常值或者规律，如果可以的话再帮我画几张图表展示一下，拜托了！"),

    ("持仓诊断",
     "我之前买了几只ETF，包括512480半导体ETF、513650标普500ETF还有511010国债ETF。我想请你帮我做一个全面的分析，包括看看每只ETF的收益率怎么样、风险大不大、溢价有没有问题、资金是在流入还是流出、还有没有更好的同类ETF可以选择。另外也帮我看看目前的宏观环境适不适合继续持有这些ETF。如果你能给我一些调仓建议就更好了，非常感谢你的帮助！"),

    ("复杂指令",
     "请你用面向对象的方式写一个Python类，这个类需要包含以下功能：连接数据库、执行SQL查询、将查询结果转换成JSON格式、支持分页查询、以及自动重连机制。代码需要有完整的错误处理和日志记录。"),

    ("多步任务",
     "第一步：从网站上爬取最新的新闻标题和链接。第二步：对爬取到的新闻进行分类，分成科技、财经、体育三类。第三步：把分类好的新闻保存到数据库里面。第四步：生成一个简单的HTML页面来展示这些新闻。如果遇到反爬虫机制，需要自动切换User-Agent和代理IP。"),
]


def benchmark():
    total_orig = 0
    total_comp = 0

    print("PromptPress v2 —— 压缩测试")
    print("=" * 60)

    for name, case in TEST_CASES:
        result = compress(case)
        r = ratio(case, result)
        total_orig += len(case)
        total_comp += len(result)

        print(f"\n【{name}】")
        print(f"  原始({len(case)}字): {case[:70]}...")
        print(f"  压缩({len(result)}字): {result[:70]}...")
        print(f"  📦 压缩率: {r}%")

    overall = ratio(str(total_orig), str(total_comp))  # approximate
    # 正确计算
    overall_real = round((1 - total_comp / total_orig) * 100, 1)
    print(f"\n{'='*60}")
    print(f"📊 整体压缩率: {overall_real}% ({total_orig} → {total_comp} 字)")
    token_saved_pct = overall_real
    print(f"💸 相当于每月省 {token_saved_pct}% token 费用")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "bench":
        benchmark()
    elif len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        result = compress(text)
        r = ratio(text, result)
        print(f"📦 {r}% | {len(text)} → {len(result)} 字")
        print(result)
    else:
        text = sys.stdin.read().strip()
        if text:
            result = compress(text)
            r = ratio(text, result)
            print(f"📦 {r}% | {len(text)} → {len(result)} 字")
            print(result)
        else:
            benchmark()
