"""
DevPilot —— 个人开发助手
聚合所有 ZCode 工具数据，统一入口，回答一切
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

HOME = Path.home()
ZCODE = HOME / ".zcode"

# 所有工具的数据源
DATA_SOURCES = {
    "portfolio":    ZCODE / "portfolio.json",
    "codegraph":    ZCODE / "codegraph" / "codegraph_index.json",
    "tokentrack":   ZCODE / "tokentrack" / "sessions.json",
    "changeguard":  ZCODE / "changeguard" / "snapshot.json",
    "skills":       HOME / ".agents" / "skills",
    "config":       ZCODE / "cli" / "config.json",
    "posterpro":    HOME / "Desktop" / "posterpro",
    "publishpro":   HOME / "Desktop" / "publishpro",
}


def _load_json(path: Path) -> Optional[dict]:
    """安全加载 JSON。"""
    if path.exists():
        try:
            return json.loads(path.read_text())
        except Exception:
            pass
    return None


# ═══════════════════════════════════════════════
#  数据聚合
# ═══════════════════════════════════════════════

def gather() -> dict:
    """聚合所有工具的最新数据。"""
    report = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "portfolio": {},
        "code": {},
        "spending": {},
        "security": {},
        "skills": {},
        "config": {},
    }

    # 1. 持仓
    pf = _load_json(DATA_SOURCES["portfolio"])
    if pf:
        holdings = pf.get("holdings", {})
        report["portfolio"] = {
            "positions": len(holdings),
            "cash": pf.get("cash", 0),
            "total_value": sum(h["shares"] * h["cost"] for h in holdings.values()) + pf.get("cash", 0),
            "alerts": len(pf.get("alerts", [])),
            "updated": pf.get("updated", ""),
        }

    # 2. 代码库
    cg = _load_json(DATA_SOURCES["codegraph"])
    if cg:
        files = cg.get("files", {})
        report["code"] = {
            "files": len(files),
            "lines": sum(f.get("lines", 0) for f in files.values()),
            "functions": len(cg.get("functions", [])),
            "classes": len(cg.get("classes", [])),
            "api_routes": len(cg.get("api_routes", [])),
            "db_tables": len(cg.get("db_tables", [])),
            "root": cg.get("root", ""),
            "scanned": True,
        }

    # 3. 费用
    tt = _load_json(DATA_SOURCES["tokentrack"])
    if tt:
        today = datetime.now().strftime("%Y-%m-%d")
        month_start = datetime.now().strftime("%Y-%m") + "-01"
        today_cost = sum(s.get("estimated_cost", 0) for s in tt if s.get("start", "")[:10] == today)
        month_cost = sum(s.get("estimated_cost", 0) for s in tt if s.get("start", "")[:7] == month_start[:7])
        all_cost = sum(s.get("estimated_cost", 0) for s in tt)
        report["spending"] = {
            "sessions": len(tt),
            "today": round(today_cost, 4),
            "this_month": round(month_cost, 2),
            "all_time": round(all_cost, 2),
        }

    # 4. 安全
    cg_snap = _load_json(DATA_SOURCES["changeguard"])
    if cg_snap:
        snap_time = cg_snap.get("time", "")
        report["security"] = {
            "last_snapshot": snap_time[:19] if snap_time else "never",
            "files_tracked": len(cg_snap.get("files", {})),
        }

    # 5. 技能
    skills_dir = DATA_SOURCES["skills"]
    if skills_dir.exists():
        skill_count = len([d for d in skills_dir.iterdir() if d.is_dir() and (d / "SKILL.md").exists()])
        report["skills"] = {
            "installed": skill_count,
        }

    # 6. MCP 配置
    cfg = _load_json(DATA_SOURCES["config"])
    if cfg:
        mcp = cfg.get("mcp", {}).get("servers", {})
        hooks = cfg.get("hooks", {})
        report["config"] = {
            "mcp_servers": len(mcp),
            "hooks_enabled": hooks.get("enabled", False),
        }

    return report


# ═══════════════════════════════════════════════
#  报告生成
# ═══════════════════════════════════════════════

def dashboard() -> str:
    """生成完整的开发环境仪表盘。"""
    d = gather()

    lines = [
        "# 🏠 开发环境仪表盘",
        f"> {d['time']}",
        "",
        "## 💰 投资组合",
    ]

    pf = d["portfolio"]
    if pf:
        lines.append(f"- 📊 {pf['positions']} 个持仓　|　💵 现金 ¥{pf['cash']:,.0f}　|　📦 总资产 ¥{pf['total_value']:,.0f}")
        lines.append(f"- 🔔 {pf['alerts']} 条活跃预警")
    else:
        lines.append("- 📭 未配置。用 `/portfolio add` 添加")

    lines.append("")
    lines.append("## 💻 代码库")

    code = d["code"]
    if code.get("scanned"):
        lines.append(f"- 📁 {code['files']} 个文件　|　📝 {code['lines']:,} 行代码")
        lines.append(f"- 🔧 {code['functions']} 个函数　|　📦 {code['classes']} 个类")
        lines.append(f"- 🌐 {code['api_routes']} 个 API 路由　|　🗄️ {code['db_tables']} 张数据库表")
    else:
        lines.append("- 📭 未扫描。用 CodeGraph 扫描")

    lines.append("")
    lines.append("## 💸 AI 费用")

    sp = d["spending"]
    if sp:
        lines.append(f"- 📅 今日：${sp['today']:.4f}　|　🗓️ 本月：${sp['this_month']:.2f}　|　📊 累计：${sp['all_time']:.2f}")
        lines.append(f"- 📈 共 {sp['sessions']} 次会话")
    else:
        lines.append("- 📭 无记录")

    lines.append("")
    lines.append("## 🛡️ 安全")

    sec = d["security"]
    if sec:
        lines.append(f"- 📸 上次快照：{sec['last_snapshot']}　|　📁 追踪 {sec['files_tracked']} 个文件")
    else:
        lines.append("- 📭 未配置快照")

    lines.append("")
    lines.append("## 🧰 工具链")

    sk = d["skills"]
    cfg = d["config"]
    lines.append(f"- 📦 {sk['installed']} 个 ZCode 技能已安装")
    lines.append(f"- 🔌 {cfg['mcp_servers']} 个 MCP 服务器已配置")
    lines.append(f"- ⚡ Hooks：{'✅ 已启用' if cfg['hooks_enabled'] else '❌ 未启用'}")

    # 内容工具
    pp = DATA_SOURCES["posterpro"]
    pb = DATA_SOURCES["publishpro"]
    poster_count = len(list(pp.glob("*.png"))) if pp.exists() else 0
    publish_count = len(list(pb.glob("*.txt"))) if pb.exists() else 0
    if poster_count or publish_count:
        lines.append(f"- 🎨 PosterPro：{poster_count} 张封面 | 📤 PublishPro：{publish_count} 个发布文件")

    lines.append("")
    lines.append("---")
    lines.append("💡 试试问：「今天有什么需要关注的」「我的开发环境健康吗」")

    return "\n".join(lines)


def quick_check() -> str:
    """快速健康检查。"""
    d = gather()
    issues = []

    if not d["code"].get("scanned"):
        issues.append("⚠️ 项目未扫描，运行 CodeGraph")
    if d["spending"].get("this_month", 0) > 10:
        issues.append(f"⚠️ 本月 AI 费用已达 ${d['spending']['this_month']:.2f}")
    if d["security"].get("last_snapshot", "never") == "never":
        issues.append("⚠️ 未配置代码快照，运行 ChangeGuard")
    if d["skills"]["installed"] < 10:
        issues.append(f"💡 仅 {d['skills']['installed']} 个技能，可以用 SkillVault 搜索更多")

    if not issues:
        return "✅ 开发环境一切正常！"

    return "## 🔍 快速检查\n\n" + "\n".join(issues)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dashboard"

    if cmd == "dashboard":
        print(dashboard())
    elif cmd == "check":
        print(quick_check())
    elif cmd == "json":
        print(json.dumps(gather(), ensure_ascii=False, indent=2))
    else:
        print("用法: devpilot [dashboard|check|json]")


if __name__ == "__main__":
    main()
