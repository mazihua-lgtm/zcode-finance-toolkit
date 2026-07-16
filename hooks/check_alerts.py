#!/usr/bin/env python3
"""
价格预警检查 —— 定时运行，检测是否触发预警条件
用法：python3 check_alerts.py  （可从 cron 或手动调用）
"""

import json
import sys
from datetime import datetime
from pathlib import Path

PORTFOLIO_FILE = Path.home() / ".zcode" / "portfolio.json"
ALERT_LOG = Path.home() / ".zcode" / "alert_log.json"


def check_alerts() -> list[dict]:
    """检查所有活跃预警，返回触发的预警列表。"""
    if not PORTFOLIO_FILE.exists():
        return []

    portfolio = json.loads(PORTFOLIO_FILE.read_text())
    alerts = portfolio.get("alerts", [])
    holdings = portfolio.get("holdings", {})

    triggered = []

    for alert in alerts:
        if not alert.get("enabled"):
            continue

        code = alert["code"]
        alert_type = alert["type"]
        threshold = alert["threshold"]

        # 这里需要调用 API 获取实时数据。当前 API 不可用时跳过。
        # 结构已预留，API 恢复后直接填充。
        try:
            # TODO: 接入实时行情查询
            # current = fetch_realtime(code)
            pass
        except Exception:
            continue

    # 记录检查时间
    log = {"last_check": datetime.now().isoformat(), "triggered": len(triggered)}
    ALERT_LOG.write_text(json.dumps(log, ensure_ascii=False, indent=2))

    return triggered


def list_alerts() -> str:
    """列出所有预警。"""
    if not PORTFOLIO_FILE.exists():
        return "📭 暂无预警。用 `/portfolio alert <代码> <类型> <阈值>` 添加。"

    portfolio = json.loads(PORTFOLIO_FILE.read_text())
    alerts = portfolio.get("alerts", [])

    if not alerts:
        return "📭 暂无活跃预警。"

    lines = ["## 🔔 活跃预警", ""]
    for a in alerts:
        status = "✅" if a.get("enabled") else "⏸️"
        lines.append(f"- {status} **{a['code']}**：{a['type']} 阈值 {a['threshold']}（{a.get('created','')}）")
    return "\n".join(lines)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print(list_alerts())
    else:
        triggered = check_alerts()
        if triggered:
            print(f"🚨 {len(triggered)} 条预警触发！")
            for t in triggered:
                print(f"  - {t}")
        else:
            print("✅ 所有预警正常，未触发。")
