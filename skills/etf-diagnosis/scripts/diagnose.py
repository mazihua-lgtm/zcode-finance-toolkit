"""
ETF 持仓诊断 — Skill 脚本
用法: python3 diagnose.py 512480 513650
"""

import sys
from pathlib import Path

# 将项目根加入路径
import os
PROJECT = Path(os.environ.get("ZCODE_PROJECT", Path.home() / "ZCodeProject"))
sys.path.insert(0, str(PROJECT))

from etf_diagnose.analyzer import (
    fetch_etf_metrics,
    fetch_peer_ranking,
    fetch_macro_context,
)
from etf_diagnose.reporter import generate_report

codes = sys.argv[1:]
if not codes:
    print("用法: python3 diagnose.py <code1> <code2> ...")
    sys.exit(1)

codes = [c.split(".")[0] for c in codes]

print(f"🔍 诊断 {len(codes)} 只 ETF: {', '.join(codes)}")
print()

print("[1/3] 拉取核心指标...")
metrics = fetch_etf_metrics(codes)
print(f"   ✅ {len(metrics)} 只")

print("[2/3] 拉取同类排名...")
peers = fetch_peer_ranking("A股半导体芯片类ETF，按近一年收益率排名前10")
print(f"   ✅ {len(peers)} 条")

print("[3/3] 拉取宏观背景...")
macro = fetch_macro_context()
print(f"   ✅ 完成")

flows = {m.code: {"主力净流入": m.main_inflow} for m in metrics if m.main_inflow != 0}

report = generate_report(metrics, peers, macro, flows)
out = PROJECT / "etf_diagnosis_report.md"
out.write_text(report, encoding="utf-8")
print(f"\n📄 报告: {out}")
print(report[:2000])
