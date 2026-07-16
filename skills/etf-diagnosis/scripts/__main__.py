"""
ETF 持仓诊断工具 —— 主入口

用法：
    python3 -m etf_diagnose 512480 513650
"""

import sys
from pathlib import Path

from .analyzer import (
    ETFMetrics,
    fetch_etf_metrics,
    fetch_peer_ranking,
    fetch_macro_context,
    fetch_fund_flows,
)
from .reporter import generate_report


def diagnose(codes: list[str], category: str = "半导体芯片") -> str:
    """
    主流程：
    1. 拉核心指标
    2. 拉同类排名
    3. 拉资金流向
    4. 拉宏观
    5. 生成报告
    """

    print(f"🔍 正在分析 {len(codes)} 只 ETF：{', '.join(codes)}")
    print()

    # --- 第1步：核心指标 ---
    print("⏳ [1/4] 正在拉取核心指标（夏普、回撤、溢价率...）")
    try:
        metrics = fetch_etf_metrics(codes)
        print(f"   ✅ 完成，获取 {len(metrics)} 只 ETF 数据")
    except Exception as e:
        print(f"   ❌ 失败: {e}")
        return f"# 获取数据失败\n\n{e}"

    # --- 第2步：同类排名 ---
    print("⏳ [2/4] 正在拉取同类 ETF 排名...")
    peers = []
    try:
        peers = fetch_peer_ranking(
            f"A股{category}类ETF，按近一年收益率排名前10"
        )
        print(f"   ✅ 完成，获取 {len(peers)} 条排名")
    except Exception as e:
        print(f"   ⚠️ 跳过（{e}）")

    # --- 第3步：资金流向（已在第1步获取）---
    print("⏳ [3/4] 正在提取资金流向...")
    flows = {}
    for m in metrics:
        if m.main_inflow != 0:
            flows[m.code] = {"主力净流入": m.main_inflow}
    print(f"   ✅ 完成")

    # --- 第4步：宏观 ---
    print("⏳ [4/4] 正在拉取宏观背景...")
    macro = ""
    try:
        macro = fetch_macro_context()
        print(f"   ✅ 完成")
    except Exception as e:
        print(f"   ⚠️ 跳过（{e}）")

    # --- 生成报告 ---
    print()
    print("📝 正在生成报告...")
    report = generate_report(metrics, peers, macro, flows)

    # 保存
    output_path = Path.cwd() / "etf_diagnose_report.md"
    output_path.write_text(report, encoding="utf-8")
    print(f"📄 报告已保存: {output_path}")

    return report


def main():
    if len(sys.argv) < 2:
        print("用法: python3 -m etf_diagnose <code1> <code2> ...")
        print("示例: python3 -m etf_diagnose 512480 513650")
        sys.exit(1)

    codes = sys.argv[1:]
    # 清洗输入（去掉可能的 SH/SZ 后缀）
    codes = [c.split(".")[0] if "." in c else c for c in codes]

    report = diagnose(codes)
    print()
    print("=" * 60)
    print(report[:3000])
    if len(report) > 3000:
        print(f"\n... (报告全长 {len(report)} 字符，完整版见 etf_diagnose_report.md)")


if __name__ == "__main__":
    main()
