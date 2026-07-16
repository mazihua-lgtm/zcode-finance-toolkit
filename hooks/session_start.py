#!/usr/bin/env python3
"""
ZCode SessionStart Hook —— 会话开始时自动执行
1. 检查是否有持仓
2. 检查 API 是否可用
3. 如果可用，快速扫描机会
4. 输出到 stdout，ZCode 会注入到对话上下文
"""

import sys
import json
from pathlib import Path

PORTFOLIO_FILE = Path.home() / ".zcode" / "portfolio.json"

def main():
    # 检查持仓
    if not PORTFOLIO_FILE.exists():
        print("💡 你还没有持仓记录。用 `/portfolio add <代码> <份数> <成本价>` 开始记录。")
        return

    portfolio = json.loads(PORTFOLIO_FILE.read_text())
    holdings = portfolio.get("holdings", {})
    if not holdings:
        return

    # 输出持仓摘要
    codes = list(holdings.keys())
    names = [f"{h['name']}({c})" for c, h in holdings.items()]
    print(f"📌 当前持仓：{', '.join(names)}")
    print(f"💵 现金：¥{portfolio.get('cash', 0):,.0f}")

    # 检查 API 是否可用
    try:
        import httpx
        r = httpx.get("https://ai-saas.eastmoney.com/proxy/b/mcp/tool/searchData", timeout=3)
        api_ok = r.status_code == 200
    except Exception:
        api_ok = False

    if api_ok:
        print("🔍 API 可用，可以运行 ETF 诊断或机会扫描。")
        print("试试说：「扫一下ETF机会」或「分析我的持仓」")
    else:
        print("⚠️ API 暂不可用（积分不足或网络问题），诊断功能受限。")

    # 检查预警
    alerts = portfolio.get("alerts", [])
    enabled_alerts = [a for a in alerts if a.get("enabled")]
    if enabled_alerts:
        print(f"🔔 {len(enabled_alerts)} 条活跃预警。")

if __name__ == "__main__":
    main()
