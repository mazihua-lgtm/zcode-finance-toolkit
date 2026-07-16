"""
ETF 持仓诊断报告生成器
"""

from datetime import datetime
from typing import Optional
from .analyzer import ETFMetrics


def generate_report(
    holdings: list[ETFMetrics],
    peers: Optional[list[dict]] = None,
    macro: Optional[str] = None,
    flows: Optional[dict] = None,
) -> str:
    """生成完整的 Markdown 诊断报告。"""

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines: list[str] = []

    # ---- 标题 ----
    lines.append(f"# 📊 ETF 持仓诊断报告")
    lines.append(f"> 生成时间：{now}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ---- 一、持仓快照 ----
    lines.append("## 一、持仓快照")
    lines.append("")
    header = "| 代码 | 名称 | 现价 | 今日 | 市值 |"
    sep = "|------|------|------|------|------|"
    lines.append(header)
    lines.append(sep)
    for h in holdings:
        name = h.name or h.code
        lines.append(
            f"| {h.code} | {name} | {h.price:.3f} | "
            f"{h.change_pct:+.2f}% | — |"
        )
    lines.append("")

    # ---- 二、核心指标对比 ----
    lines.append("## 二、核心指标对比")
    lines.append("")
    header2 = "| 指标 | " + " | ".join(f"{h.code}" for h in holdings) + " |"
    sep2 = "|------|" + "|".join("------:" for _ in holdings) + "|"
    lines.append(header2)
    lines.append(sep2)

    rows_metrics = [
        ("近1月回报", [f"{h.ret_1m:+.1f}%" if h.ret_1m else "—" for h in holdings]),
        ("近3月回报", [f"{h.ret_3m:+.1f}%" if h.ret_3m else "—" for h in holdings]),
        ("近1年回报", [f"{h.ret_1y:+.1f}%" if h.ret_1y else "—" for h in holdings]),
        ("夏普比率", [f"{h.sharpe:.2f}" if h.sharpe else "数据暂缺" for h in holdings]),
        ("年化波动率", [f"{h.volatility:.1f}%" if h.volatility else "—" for h in holdings]),
        ("近1年最大回撤", [f"{h.max_drawdown_1y:.1f}%" if h.max_drawdown_1y else "数据暂缺" for h in holdings]),
        ("溢价率", [f"{h.premium:.2f}%" if h.premium else "—" for h in holdings]),
        ("净值", [f"{h.nav:.3f}" if h.nav else "—" for h in holdings]),
    ]
    for label, vals in rows_metrics:
        lines.append(f"| {label} | " + " | ".join(vals) + " |")
    lines.append("")

    # ---- 三、逐标诊断 ----
    lines.append("## 三、逐标诊断")
    lines.append("")
    for h in holdings:
        name = h.name or h.code
        lines.append(f"### {h.code} {name}")
        lines.append("")
        lines.append(f"| 维度 | 评估 |")
        lines.append(f"|------|------|")
        lines.append(f"| 收益表现 | 近1年 **{h.ret_1y:+.1f}%**，近3月 **{h.ret_3m:+.1f}%** |")
        lines.append(f"| 风险调整 | 夏普 **{h.sharpe:.2f}** → {h.sharpe_grade} |")
        lines.append(f"| 波动水平 | 年化波动 **{h.volatility:.1f}%** |")
        lines.append(f"| 最大回撤 | **{h.max_drawdown_1y:.1f}%** |")
        lines.append(f"| 溢价情况 | **{h.premium:.2f}%** {'⚠️ 偏高，注意风险' if h.premium > 3 else '✅ 正常'} |")

        if h.warnings:
            lines.append("")
            lines.append("**⚠️ 风险提醒：**")
            for w in h.warnings:
                lines.append(f"- {w}")
        lines.append("")

    # ---- 四、同赛道排名 ----
    if peers:
        lines.append("## 四、同赛道 ETF 对比")
        lines.append("")
        headers = list(peers[0].keys())[:6] if peers else []
        if headers:
            lines.append("| " + " | ".join(headers[:6]) + " |")
            lines.append("|" + "|".join(["------" for _ in headers[:6]]) + "|")
            for row in peers[:10]:
                vals = [str(row.get(k, "")) for k in headers[:6]]
                lines.append("| " + " | ".join(vals) + " |")
        lines.append("")

    # ---- 五、资金流向 ----
    if flows:
        lines.append("## 五、资金流向")
        lines.append("")
        for code, flow in flows.items():
            inflow = flow.get("主力净流入", 0)
            direction = "🟢 流入" if inflow > 0 else "🔴 流出"
            # inflow 单位已是「亿元」
            lines.append(f"- **{code}**：主力净流入 {inflow:+.4f} 亿 {direction}")
        lines.append("")

    # ---- 六、宏观背景 ----
    if macro:
        lines.append("## 六、宏观背景")
        lines.append("")
        # 截取关键部分
        summary = macro[:1500]
        if len(macro) > 1500:
            summary += "\n\n> ...(完整内容已截断)"
        lines.append(summary)
        lines.append("")

    # ---- 七、调仓参考 ----
    lines.append("## 七、调仓参考")
    lines.append("")

    if holdings:
        # 夏普最高和最低
        best = max(holdings, key=lambda h: h.sharpe)
        worst = min(holdings, key=lambda h: h.sharpe)
        lines.append(f"- **最优资产**：{best.code} {best.name}（夏普 {best.sharpe:.2f}）")
        lines.append(f"- **最弱资产**：{worst.code} {worst.name}（夏普 {worst.sharpe:.2f}）")
    lines.append("")
    lines.append("> ⚠️ 以上为数据驱动的客观分析，不构成买卖建议。投资决策请自行判断。")

    return "\n".join(lines)
