"""
TokenTrack —— AI 费用追踪器

- 自动记录每次会话
- 估算 token 消耗和费用
- 生成日报/周报/月报
"""

import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

STORAGE = Path.home() / ".zcode" / "tokentrack"
LOG_FILE = STORAGE / "sessions.json"

# DeepSeek V4 Pro 定价（$/1M tokens）
PRICING = {
    "deepseek-v4-pro": {"input": 0.55, "output": 2.19},
    "deepseek-chat":    {"input": 0.14, "output": 0.28},
    "claude-sonnet-4":  {"input": 3.00, "output": 15.00},
    "claude-opus-4":    {"input": 15.00, "output": 75.00},
    "default":          {"input": 1.00, "output": 4.00},
}

# 估算参数
AVG_INPUT_TOKENS_PER_EXCHANGE = 2000   # 每次对话约 2000 输入 token
AVG_OUTPUT_TOKENS_PER_EXCHANGE = 500   # 每次回复约 500 输出 token
AVG_TOOL_CALL_TOKENS = 5000            # 每次工具调用约额外 5000 token


def _load() -> list[dict]:
    STORAGE.mkdir(parents=True, exist_ok=True)
    if LOG_FILE.exists():
        return json.loads(LOG_FILE.read_text())
    return []


def _save(sessions: list[dict]):
    LOG_FILE.write_text(json.dumps(sessions, ensure_ascii=False, indent=2))


def start_session(project: str = "", model: str = "deepseek-v4-pro") -> dict:
    """开始新会话，返回 session 对象。"""
    return {
        "id": datetime.now().strftime("%Y%m%d-%H%M%S"),
        "project": project or Path.cwd().name,
        "model": model,
        "start": datetime.now().isoformat(),
        "exchanges": 0,
        "tool_calls": 0,
        "end": None,
        "estimated_tokens": 0,
        "estimated_cost": 0.0,
    }


def end_session(session: dict):
    """结束会话，计算费用，存入日志。"""
    session["end"] = datetime.now().isoformat()
    exchanges = session.get("exchanges", 10)
    tool_calls = session.get("tool_calls", 5)

    total_input = exchanges * AVG_INPUT_TOKENS_PER_EXCHANGE + tool_calls * AVG_TOOL_CALL_TOKENS
    total_output = exchanges * AVG_OUTPUT_TOKENS_PER_EXCHANGE

    pricing = PRICING.get(session.get("model", ""), PRICING["default"])
    cost = (total_input / 1_000_000) * pricing["input"] + (total_output / 1_000_000) * pricing["output"]

    session["estimated_tokens"] = total_input + total_output
    session["estimated_cost"] = round(cost, 4)

    sessions = _load()
    sessions.append(session)
    _save(sessions)

    return session


def add_exchange(session: dict, count: int = 1):
    """记录一次对话轮次。"""
    session["exchanges"] = session.get("exchanges", 0) + count


def add_tool_call(session: dict, count: int = 1):
    """记录一次工具调用。"""
    session["tool_calls"] = session.get("tool_calls", 0) + count


def get_current_session() -> dict:
    """获取或创建当前会话。"""
    sessions = _load()
    # 找今天最后一个未结束的会话
    today = datetime.now().strftime("%Y%m%d")
    for s in reversed(sessions):
        if s["id"].startswith(today) and not s.get("end"):
            return s
    return start_session()


# ═══════════════════════════════════════════════
#  统计报告
# ═══════════════════════════════════════════════

def stats(days: int = 30) -> dict:
    """统计最近 N 天的费用。"""
    sessions = _load()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    recent = [s for s in sessions if s.get("start", "") >= cutoff]

    total_cost = sum(s.get("estimated_cost", 0) for s in recent)
    total_tokens = sum(s.get("estimated_tokens", 0) for s in recent)
    total_sessions = len(recent)

    # 按项目分组
    by_project = defaultdict(lambda: {"cost": 0.0, "tokens": 0, "sessions": 0})
    for s in recent:
        proj = s.get("project", "unknown")
        by_project[proj]["cost"] += s.get("estimated_cost", 0)
        by_project[proj]["tokens"] += s.get("estimated_tokens", 0)
        by_project[proj]["sessions"] += 1

    # 按天分组
    by_day = defaultdict(float)
    for s in recent:
        day = s.get("start", "")[:10]
        by_day[day] += s.get("estimated_cost", 0)

    return {
        "days": days,
        "total_cost": round(total_cost, 2),
        "total_tokens": total_tokens,
        "total_sessions": total_sessions,
        "avg_per_session": round(total_cost / total_sessions, 2) if total_sessions else 0,
        "by_project": dict(by_project),
        "by_day": dict(sorted(by_day.items())),
    }


def format_report(days: int = 30) -> str:
    """生成可读的费用报告。"""
    s = stats(days)
    period = f"近{days}天" if days <= 30 else f"近{days//30}个月"

    lines = [
        f"# 💰 AI 费用报告（{period}）",
        "",
        f"| 指标 | 数值 |",
        f"|------|------|",
        f"| 会话数 | {s['total_sessions']} 次 |",
        f"| Token 消耗 | {s['total_tokens']:,} |",
        f"| **总费用** | **${s['total_cost']:.2f}** |",
        f"| 平均每次 | ${s['avg_per_session']:.2f} |",
        "",
    ]

    if s["by_project"]:
        lines.append("## 📂 按项目")
        lines.append("")
        for proj, data in sorted(s["by_project"].items(), key=lambda x: x[1]["cost"], reverse=True):
            pct = (data["cost"] / s["total_cost"] * 100) if s["total_cost"] > 0 else 0
            bar = "█" * int(pct / 5)
            lines.append(f"- **{proj}**：${data['cost']:.2f}（{pct:.0f}%）{bar}")
        lines.append("")

    if s["by_day"]:
        lines.append("## 📅 每日趋势")
        lines.append("")
        # 文本柱状图
        max_cost = max(s["by_day"].values()) if s["by_day"] else 1
        for day, cost in s["by_day"].items():
            bar_len = int(cost / max_cost * 20) if max_cost > 0 else 0
            bar = "█" * bar_len
            lines.append(f"- {day}：${cost:.2f} {bar}")
        lines.append("")

    # 预估月度费用
    if s["days"] > 0 and s["total_cost"] > 0:
        daily_avg = s["total_cost"] / s["days"]
        monthly_est = daily_avg * 30
        lines.append(f"📊 **预估月费**：约 **${monthly_est:.2f}**（日均 ${daily_avg:.2f}）")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"

    if cmd == "start":
        s = start_session()
        print(f"✅ 会话开始: {s['id']}")

    elif cmd == "end":
        sessions = _load()
        if sessions and not sessions[-1].get("end"):
            s = end_session(sessions[-1])
            print(f"✅ 会话结束: {s['id']}")
            print(f"   预估费用: ${s['estimated_cost']:.4f}")
        else:
            print("⚠️ 没有活跃会话")

    elif cmd == "report":
        days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        print(format_report(days))

    elif cmd == "log":
        # 记录一次对话（用于手动追踪）
        s = get_current_session()
        s["exchanges"] = s.get("exchanges", 0) + 1
        sessions = _load()
        # 更新或追加
        updated = False
        for i, sess in enumerate(sessions):
            if sess["id"] == s["id"]:
                sessions[i] = s
                updated = True
                break
        if not updated:
            sessions.append(s)
        _save(sessions)

    else:
        print("用法: tokentrack [start|end|report|log]")


if __name__ == "__main__":
    main()
