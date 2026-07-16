"""
Portfolio 状态管理 —— 跨会话持久化用户持仓

存储格式：~/.zcode/portfolio.json
{
  "holdings": {
    "512480": {"code": "512480", "name": "半导体ETF", "shares": 1000, "cost": 1.471, "added": "2026-07-09"},
    "513650": {"code": "513650", "name": "标普500ETF", "shares": 1900, "cost": 1.900, "added": "2026-07-09"}
  },
  "cash": 1300,
  "alerts": [
    {"code": "512480", "type": "premium_above", "threshold": 5.0, "enabled": true},
    {"code": "512480", "type": "drawdown", "threshold": -10.0, "enabled": true}
  ],
  "updated": "2026-07-16T10:00:00"
}
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

PORTFOLIO_FILE = Path.home() / ".zcode" / "portfolio.json"


def load() -> dict:
    """加载持仓数据。"""
    if not PORTFOLIO_FILE.exists():
        return {"holdings": {}, "cash": 0, "alerts": [], "updated": ""}
    return json.loads(PORTFOLIO_FILE.read_text())


def save(data: dict):
    """保存持仓数据。"""
    data["updated"] = datetime.now().isoformat()
    PORTFOLIO_FILE.parent.mkdir(parents=True, exist_ok=True)
    PORTFOLIO_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def add_holding(code: str, name: str, shares: int, cost: float) -> dict:
    """添加或更新一只持仓。"""
    data = load()
    data["holdings"][code] = {
        "code": code,
        "name": name,
        "shares": shares,
        "cost": cost,
        "added": datetime.now().strftime("%Y-%m-%d"),
    }
    save(data)
    return data


def remove_holding(code: str) -> dict:
    """删除一只持仓。"""
    data = load()
    data["holdings"].pop(code, None)
    save(data)
    return data


def set_cash(amount: float) -> dict:
    """设置现金余额。"""
    data = load()
    data["cash"] = amount
    save(data)
    return data


def add_alert(code: str, alert_type: str, threshold: float) -> dict:
    """添加一个预警。类型：premium_above / drawdown / price_below / price_above"""
    data = load()
    data.setdefault("alerts", []).append({
        "code": code,
        "type": alert_type,
        "threshold": threshold,
        "enabled": True,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
    })
    save(data)
    return data


def format_summary() -> str:
    """生成持仓摘要文本。"""
    data = load()
    holdings = data.get("holdings", {})
    cash = data.get("cash", 0)
    alerts = data.get("alerts", [])

    if not holdings and cash == 0:
        return "📭 暂无持仓记录。用 `/portfolio add <代码> <份数> <成本价>` 添加。"

    lines = ["## 📌 我的持仓", ""]
    total_value = cash
    for code, h in holdings.items():
        name = h.get("name", code)
        shares = h["shares"]
        cost = h["cost"]
        current_value = cost * shares  # 需实时查询更新
        total_value += current_value
        lines.append(f"| {code} | {name} | {shares} 份 | 成本 ¥{cost:.3f} | 市值约 ¥{current_value:.0f} |")

    lines.append(f"\n💵 现金：¥{cash:,.0f}")
    lines.append(f"📊 总资产：约 ¥{total_value:,.0f}")

    if alerts:
        enabled = [a for a in alerts if a.get("enabled")]
        if enabled:
            lines.append(f"\n🔔 活跃预警：{len(enabled)} 条")

    return "\n".join(lines)


# ---- CLI ----
if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "show"

    if cmd == "show":
        print(format_summary())
    elif cmd == "add" and len(sys.argv) >= 5:
        add_holding(sys.argv[2], sys.argv[3], int(sys.argv[4]), float(sys.argv[5]))
        print(f"✅ 已添加 {sys.argv[2]}")
    elif cmd == "remove" and len(sys.argv) >= 3:
        remove_holding(sys.argv[2])
        print(f"✅ 已移除 {sys.argv[2]}")
    elif cmd == "cash" and len(sys.argv) >= 3:
        set_cash(float(sys.argv[2]))
        print(f"✅ 现金更新为 {sys.argv[2]}")
    elif cmd == "alert" and len(sys.argv) >= 5:
        add_alert(sys.argv[2], sys.argv[3], float(sys.argv[4]))
        print(f"✅ 已添加预警: {sys.argv[2]} {sys.argv[3]} {sys.argv[4]}")
    else:
        print("用法: portfolio.py [show|add|remove|cash|alert] ...")
