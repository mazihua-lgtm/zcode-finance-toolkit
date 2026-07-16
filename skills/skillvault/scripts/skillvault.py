"""
SkillVault —— ZCode 技能注册表
扫描本地技能、搜索、统计、一键安装
"""

import re
import sys
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

SKILL_DIRS = [
    Path.home() / ".agents" / "skills",
    Path.home() / ".zcode" / "skills",
]


@dataclass
class Skill:
    name: str
    path: Path
    description: str = ""
    has_scripts: bool = False
    triggers: list[str] = field(default_factory=list)
    category: str = "其他"

    @property
    def short_desc(self) -> str:
        return self.description[:80] + "..." if len(self.description) > 80 else self.description


def scan() -> list[Skill]:
    """扫描所有已安装的技能。"""
    skills: dict[str, Skill] = {}

    for base in SKILL_DIRS:
        if not base.exists():
            continue
        for skill_dir in base.iterdir():
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            try:
                s = _parse_skill(skill_md, skill_dir)
                if s.name not in skills:  # 先去先得（user scope 优先）
                    skills[s.name] = s
            except Exception:
                pass

    return sorted(skills.values(), key=lambda s: s.name)


def _parse_skill(skill_md: Path, skill_dir: Path) -> Skill:
    content = skill_md.read_text(encoding="utf-8")
    name = skill_dir.name

    # 提取 YAML frontmatter
    fm_match = re.match(r"^---\s*\n(.*?)\n---", content, re.DOTALL)
    description = ""
    if fm_match:
        fm = fm_match.group(1)
        for line in fm.split("\n"):
            if line.startswith("description:"):
                description = line.split(":", 1)[1].strip().strip('"').strip("'")
                # 多行描述
                if description == ">" or description == "|":
                    description = ""
                    # 从正文提取
                break

    # 如果 frontmatter 没有 description，从正文第一段提取
    if not description:
        body = content[fm_match.end():] if fm_match else content
        for line in body.split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and len(line) > 10:
                description = line[:120]
                break

    has_scripts = (skill_dir / "scripts").exists()

    # 分类
    category = "其他"
    name_lower = name.lower()
    desc_lower = description.lower()
    if any(k in name_lower for k in ["lark", "飞书"]):
        category = "飞书"
    elif any(k in desc_lower for k in ["股票", "基金", "金融", "etf", "finance", "stock"]):
        category = "金融"
    elif any(k in name_lower for k in ["mx-", "finance", "macro", "stocks"]):
        category = "金融"
    elif any(k in desc_lower for k in ["文档", "doc", "pdf", "docx"]):
        category = "文档"
    elif any(k in desc_lower for k in ["开发", "代码", "编程", "developer", "code"]):
        category = "开发"
    elif any(k in desc_lower for k in ["浏览器", "browser", "web"]):
        category = "工具"
    elif any(k in desc_lower for k in ["prompt", "token", "压缩"]):
        category = "效率"

    # 提取触发词
    triggers = []
    trigger_match = re.findall(r"[\u201c\u300c](.*?)[\u201d\u300d]", description)
    triggers.extend(trigger_match[:5])

    return Skill(
        name=name,
        path=skill_dir,
        description=description,
        has_scripts=has_scripts,
        triggers=triggers,
        category=category,
    )


def search(skills: list[Skill], query: str) -> list[Skill]:
    """按关键词搜索技能。"""
    q = query.lower()
    results = []
    for s in skills:
        score = 0
        if q in s.name.lower():
            score += 10
        if q in s.description.lower():
            score += 5
        if score > 0:
            results.append((score, s))
    results.sort(key=lambda x: x[0], reverse=True)
    return [s for _, s in results]


def stats(skills: list[Skill]) -> dict:
    """统计信息。"""
    cats = {}
    total_scripts = 0
    for s in skills:
        cats[s.category] = cats.get(s.category, 0) + 1
        if s.has_scripts:
            total_scripts += 1
    return {
        "total": len(skills),
        "with_scripts": total_scripts,
        "categories": cats,
    }


def install_from_github(repo_url: str) -> bool:
    """从 GitHub 克隆技能到本地。"""
    name = repo_url.rstrip("/").split("/")[-1]
    target = Path.home() / ".agents" / "skills" / name
    if target.exists():
        print(f"⚠️  {name} 已存在: {target}")
        return False
    try:
        subprocess.run(
            ["git", "clone", repo_url, str(target)],
            check=True, capture_output=True, text=True,
        )
        print(f"✅ 已安装: {name}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ 安装失败: {e.stderr[:200]}")
        return False


# ═══════════════════════════════════════════════
#  输出
# ═══════════════════════════════════════════════

def format_list(skills: list[Skill], show_all: bool = False) -> str:
    """格式化技能列表。"""
    lines = ["# 📦 ZCode 技能注册表", "", f"共 {len(skills)} 个技能", ""]

    # 按类别分组
    by_cat: dict[str, list] = {}
    for s in skills:
        by_cat.setdefault(s.category, []).append(s)

    for cat in ["金融", "飞书", "文档", "开发", "效率", "工具", "其他"]:
        group = by_cat.get(cat, [])
        if not group:
            continue
        lines.append(f"## {cat}（{len(group)}）")
        lines.append("")
        for s in group:
            badge = "📜" if s.has_scripts else "📄"
            lines.append(f"- {badge} **{s.name}** — {s.short_desc}")
        lines.append("")

    return "\n".join(lines)


def format_search_results(query: str, results: list[Skill]) -> str:
    """格式化搜索结果。"""
    if not results:
        return f"🔍 未找到与「{query}」相关的技能。"
    lines = [f"🔍 搜索「{query}」—— {len(results)} 个结果", ""]
    for s in results[:10]:
        lines.append(f"- **{s.name}** [{s.category}] — {s.short_desc}")
    return "\n".join(lines)


def format_stats(skills: list[Skill]) -> str:
    """格式化统计。"""
    st = stats(skills)
    lines = [
        "# 📊 技能统计",
        "",
        f"总计：**{st['total']}** 个技能",
        f"含可执行脚本：**{st['with_scripts']}** 个",
        "",
        "## 按类别",
        "",
    ]
    for cat, count in sorted(st["categories"].items(), key=lambda x: x[1], reverse=True):
        bar = "█" * min(count, 20)
        lines.append(f"- {cat}：{count} {bar}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        # 默认：列出所有
        all_skills = scan()
        print(format_list(all_skills))
        return

    cmd = sys.argv[1]

    if cmd == "list":
        all_skills = scan()
        print(format_list(all_skills))

    elif cmd == "search" and len(sys.argv) >= 3:
        query = sys.argv[2]
        all_skills = scan()
        results = search(all_skills, query)
        print(format_search_results(query, results))

    elif cmd == "stats":
        all_skills = scan()
        print(format_stats(all_skills))

    elif cmd == "install" and len(sys.argv) >= 3:
        install_from_github(sys.argv[2])

    elif cmd == "scan":
        all_skills = scan()
        print(format_stats(all_skills))
        print()
        print(format_list(all_skills))

    else:
        print("用法: skillvault [list|search <关键词>|stats|install <github-url>|scan]")


if __name__ == "__main__":
    main()
