"""
ETF 机会扫描 — Skill 脚本
用法: python3 scan.py
"""

import sys
import os
from pathlib import Path

PROJECT = Path(os.environ.get("ZCODE_PROJECT", Path.home() / "ZCodeProject"))
sys.path.insert(0, str(PROJECT))

from etf_diagnose.scanner import run_scan, generate_opportunity_report

print("🔍 全市场 ETF 机会扫描中...")
opps = run_scan()
report = generate_opportunity_report(opps)

out = PROJECT / "etf_opportunities.md"
out.write_text(report, encoding="utf-8")
print(f"\n📄 报告: {out}")
print(report[:2000])
