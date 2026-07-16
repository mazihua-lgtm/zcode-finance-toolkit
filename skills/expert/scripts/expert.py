"""
ZCode 专家系统 —— 智能技能路由 + 工作流编排

功能：
  1. 理解用户意图
  2. 匹配最佳技能
  3. 多技能编排（复杂任务自动拆解）
  4. 解释推荐理由
"""

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

SKILL_DIR = Path.home() / ".agents" / "skills"


# ═══════════════════════════════════════════════
#  技能知识库
# ═══════════════════════════════════════════════

def _load_skill_index() -> list[dict]:
    """加载所有技能的索引（名称 + 描述 + 触发词）。"""
    index = []
    if not SKILL_DIR.exists():
        return index

    for skill_dir in sorted(SKILL_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        md = skill_dir / "SKILL.md"
        if not md.exists():
            continue

        content = md.read_text(encoding="utf-8")
        fm = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
        name = skill_dir.name
        desc = ""

        if fm:
            for line in fm.group(1).split("\n"):
                if line.startswith("description:"):
                    desc = line.split(":", 1)[1].strip().strip('"').strip("'")
                    if desc in (">", "|"):
                        desc = ""
                    break

        if not desc:
            body = content[fm.end():] if fm else content
            for line in body.split("\n"):
                line = line.strip()
                if line and not line.startswith("#") and len(line) > 15:
                    desc = line[:200]
                    break

        triggers = re.findall(r"[\u201c\u300c](.*?)[\u201d\u300d]", desc)

        index.append({
            "name": name,
            "description": desc,
            "triggers": triggers[:8],
        })

    return index


# ═══════════════════════════════════════════════
#  意图 → 技能映射表（手工维护 + 自动匹配）
# ═══════════════════════════════════════════════

# 高频意图的手工映射（优先级高于自动匹配）
INTENT_MAP = {
    # 金融投资
    "etf": ["etf-diagnosis", "mx-finance-data"],
    "持仓": ["etf-diagnosis"],
    "调仓": ["etf-diagnosis"],
    "诊断": ["stock-diagnosis", "etf-diagnosis"],
    "股票": ["stock-diagnosis", "mx-finance-data", "mx-finance-search"],
    "基金": ["fund-diagnosis", "mx-finance-data"],
    "财报": ["stock-earnings-review"],
    "业绩": ["stock-earnings-review"],
    "宏观": ["mx-macro-data"],
    "选股": ["mx-stocks-screener"],
    "筛选": ["mx-stocks-screener"],
    "新闻": ["mx-finance-search"],
    "公告": ["mx-finance-search"],
    "研报": ["mx-finance-search"],
    "热点": ["stock-market-hotspot-discovery"],
    "行业": ["industry-research-report"],
    "深度": ["initiation-of-coverage-or-deep-dive"],
    "对比": ["comparable-company-analysis"],
    "知识库": ["mx-personal-kb-search"],

    # 飞书办公
    "飞书": ["lark-im", "lark-doc", "lark-calendar"],
    "消息": ["lark-im"],
    "聊天": ["lark-im"],
    "文档": ["lark-doc", "document-skills:docx"],
    "表格": ["lark-sheets", "lark-base"],
    "日历": ["lark-calendar"],
    "日程": ["lark-calendar", "lark-workflow-standup-report"],
    "会议": ["lark-vc", "lark-calendar"],
    "纪要": ["lark-workflow-meeting-summary", "lark-vc"],
    "邮件": ["lark-mail"],
    "审批": ["lark-approval"],
    "考勤": ["lark-attendance"],
    "通讯录": ["lark-contact"],
    "任务": ["lark-task"],
    "OKR": ["lark-okr"],
    "画板": ["lark-whiteboard"],
    "知识库": ["lark-wiki"],
    "文件": ["lark-drive"],

    # 工具
    "pdf": ["document-skills:pdf"],
    "word": ["document-skills:docx"],
    "浏览器": ["browser-skill"],
    "压缩": ["promptpress"],
    "token": ["promptpress"],
    "prompt": ["promptpress"],
    "省token": ["promptpress"],
    "技能": ["skillvault"],
    "安装": ["skillvault"],
    "管理": ["skillvault"],
}


def _score_skill(query: str, skill: dict) -> float:
    """计算技能与查询的相关性得分。"""
    score = 0.0
    q = query.lower()
    name = skill["name"].lower()
    desc = skill["description"].lower()

    # 名称精确匹配
    if q == name:
        score += 100
    # 名称包含
    if q in name:
        score += 50
    # 关键词在名称中
    for word in q.split():
        if len(word) >= 2 and word in name:
            score += 20

    # 描述匹配
    if q in desc:
        score += 10
    for word in q.split():
        if len(word) >= 2 and word in desc:
            score += 3

    # 触发词匹配
    for trigger in skill.get("triggers", []):
        if q in trigger.lower():
            score += 15

    return score


# ═══════════════════════════════════════════════
#  工作流模板
# ═══════════════════════════════════════════════

WORKFLOWS = {
    "投资研究": {
        "pattern": ["股票", "分析", "研究", "报告", "深度"],
        "steps": [
            ("信息收集", ["mx-finance-search"]),
            ("数据查询", ["mx-finance-data"]),
            ("深度分析", ["initiation-of-coverage-or-deep-dive"]),
            ("同行对比", ["comparable-company-analysis"]),
        ],
        "description": "从信息收集到深度报告的完整投研流程",
    },
    "持仓管理": {
        "pattern": ["持仓", "调仓", "优化", "配置"],
        "steps": [
            ("持仓诊断", ["etf-diagnosis", "stock-diagnosis"]),
            ("机会扫描", ["etf-diagnosis"]),
            ("调仓建议", ["etf-diagnosis"]),
        ],
        "description": "诊断→扫描→调仓的完整持仓管理流程",
    },
    "每日复盘": {
        "pattern": ["复盘", "今日", "市场", "热点", "总结"],
        "steps": [
            ("热点扫描", ["stock-market-hotspot-discovery"]),
            ("行情数据", ["mx-finance-data"]),
            ("重要新闻", ["mx-finance-search"]),
        ],
        "description": "每日盘后快速复盘流程",
    },
    "文档处理": {
        "pattern": ["文档", "报告", "pdf", "word", "生成"],
        "steps": [
            ("内容撰写", ["lark-doc"]),
            ("格式转换", ["document-skills:pdf", "document-skills:docx"]),
            ("云端存储", ["lark-drive"]),
        ],
        "description": "文档撰写→转换→存储的完整流程",
    },
}


# ═══════════════════════════════════════════════
#  主引擎
# ═══════════════════════════════════════════════

class ExpertSystem:
    def __init__(self):
        self.skills = _load_skill_index()

    def route(self, query: str, top_k: int = 5) -> list[dict]:
        """根据用户查询，返回最匹配的技能列表。"""
        # 先查手工映射
        manual = []
        for keyword, skills in INTENT_MAP.items():
            if keyword in query.lower():
                for s in skills:
                    manual.append({"name": s, "reason": f"匹配关键词「{keyword}」", "source": "rule"})

        # 自动评分
        scored = []
        for skill in self.skills:
            s = _score_skill(query, skill)
            if s > 0:
                scored.append((s, skill))

        scored.sort(key=lambda x: x[0], reverse=True)
        auto = [
            {"name": s["name"], "reason": f"语义匹配 {sc:.0f}分", "source": "ai"}
            for sc, s in scored[:top_k]
        ]

        # 合并：手工优先，自动补充
        seen = set()
        results = []
        for r in manual:
            if r["name"] not in seen:
                results.append(r)
                seen.add(r["name"])
        for r in auto:
            if r["name"] not in seen and len(results) < top_k:
                results.append(r)
                seen.add(r["name"])

        return results[:top_k]

    def detect_workflow(self, query: str) -> Optional[dict]:
        """检测是否匹配已知工作流。"""
        best = None
        best_score = 0
        for name, wf in WORKFLOWS.items():
            score = sum(1 for kw in wf["pattern"] if kw in query)
            if score > best_score:
                best_score = score
                best = {"name": name, **wf}

        if best_score >= 2:
            return best
        return None

    def analyze(self, query: str) -> dict:
        """完整分析：路由 + 工作流检测。"""
        skills = self.route(query)
        workflow = self.detect_workflow(query)
        return {
            "query": query,
            "skills": skills,
            "workflow": workflow,
        }


# ═══════════════════════════════════════════════
#  格式化输出
# ═══════════════════════════════════════════════

def format_result(result: dict) -> str:
    lines = [
        f"# 🧠 ZCode 专家系统",
        f"",
        f"**你的需求**：{result['query']}",
        f"",
    ]

    # 工作流
    if result["workflow"]:
        wf = result["workflow"]
        lines.append(f"## 🔄 推荐工作流：{wf['name']}")
        lines.append(f"> {wf['description']}")
        lines.append("")
        for i, (step_name, step_skills) in enumerate(wf["steps"], 1):
            lines.append(f"**第{i}步：{step_name}** → {' → '.join(f'`{s}`' for s in step_skills)}")
        lines.append("")

    # 推荐技能
    lines.append("## 🎯 推荐技能")
    lines.append("")
    for i, s in enumerate(result["skills"], 1):
        tag = "📌" if s["source"] == "rule" else "🤖"
        lines.append(f"{i}. {tag} **{s['name']}** — {s['reason']}")
    lines.append("")

    lines.append("---")
    lines.append("💡 直接说出你的需求，我会自动匹配最佳技能并编排工作流。")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    if len(sys.argv) < 2:
        print("用法: python3 expert.py <你的需求描述>")
        print("示例: python3 expert.py 帮我分析一下我的ETF持仓")
        return

    query = " ".join(sys.argv[1:])
    expert = ExpertSystem()
    result = expert.analyze(query)
    print(format_result(result))


if __name__ == "__main__":
    main()
