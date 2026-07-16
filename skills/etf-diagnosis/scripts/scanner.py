"""
ETF 机会发现引擎 —— 自动扫描 + 多维度评分

扫描维度：
  A. 折价机会   — 市价 < 净值，折价越大越好
  B. 溢价风险   — 市价 > 净值 >5%，警惕回归
  C. 资金异动   — 近期主力大幅流入/流出
  D. 超跌反弹   — 短期跌幅大 + 长期趋势未破
  E. 动量延续   — 近期强势 + 资金持续流入
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

SKILLS_DIR = Path.home() / ".agents" / "skills"
SCREENER = SKILLS_DIR / "mx-stocks-screener" / "scripts" / "get_data.py"
FINANCE_DATA = SKILLS_DIR / "mx-finance-data" / "scripts" / "get_data.py"
WORK_DIR = Path.cwd()


@dataclass
class Opportunity:
    code: str
    name: str = ""
    price: float = 0
    change_pct: float = 0
    premium: float = 0       # 溢价率，负=折价
    ret_1w: float = 0
    ret_1m: float = 0
    ret_3m: float = 0
    ret_1y: float = 0
    volume_ratio: float = 0  # 量比
    main_inflow: float = 0   # 主力净流入(亿)
    scale: float = 0         # 规模(亿)
    score: float = 0         # 综合得分
    signals: list = field(default_factory=list)
    signal_type: str = ""    # discount / inflow / momentum / oversold / premium_alert


def _run(script: Path, args: list[str], timeout: int = 60) -> str:
    """运行脚本，返回 stdout。"""
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True, text=True,
        timeout=timeout, cwd=str(WORK_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"{script.name} 失败: {result.stderr[:300]}")
    return result.stdout


def _parse_csv_path(stdout: str) -> Optional[Path]:
    """从脚本 stdout 中提取 CSV 文件路径。"""
    for line in stdout.split("\n"):
        if "CSV:" in line or "csv:" in line:
            path_str = line.split(":", 1)[1].strip()
            p = Path(path_str)
            if p.exists():
                return p
    # 回退：找最新的 csv
    return _latest_csv("miaoxiang/mx_stocks_screener/mx_stocks_screener_*.csv")


def _do_scan(query: str, select_type: str = "ETF", timeout: int = 60) -> list[dict]:
    """执行一次筛选并返回结果。"""
    try:
        stdout = _run(SCREENER, [
            "--query", query,
            "--select-type", select_type,
        ], timeout=timeout)
    except Exception as e:
        print(f"      ⚠️ 失败: {e}")
        return []
    csv_path = _parse_csv_path(stdout)
    if csv_path:
        return _read_csv(csv_path)
    return []


# ═══════════════════════════════════════════════
#  扫描任务
# ═══════════════════════════════════════════════

def _latest_csv(pattern: str) -> Optional[Path]:
    files = sorted(WORK_DIR.glob(pattern), key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0] if files else None


def _read_csv(path: Path) -> list[dict]:
    import csv
    rows = []
    with open(path, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    return rows


# ═══════════════════════════════════════════════
#  扫描任务（统一使用 _do_scan）
# ═══════════════════════════════════════════════

def scan_discount_etfs() -> list[dict]:
    return _do_scan("折价率大于1.5%的ETF，规模大于2亿，按折价率从大到小排序，取前15")

def scan_premium_etfs() -> list[dict]:
    return _do_scan("溢价率大于5%的ETF，按溢价率从大到小排序，取前10")

def scan_fund_inflow_etfs() -> list[dict]:
    return _do_scan("近5日主力资金净流入最大的ETF，规模大于5亿，按净流入排序取前10")

def scan_momentum_etfs() -> list[dict]:
    return _do_scan("近一月涨幅最大的ETF，规模大于3亿，成交额大于5000万，按涨幅排序取前10")

def scan_oversold_etfs() -> list[dict]:
    return _do_scan("近一周跌幅最大的ETF，规模大于5亿，按跌幅从大到小排序取前10")

def scan_volume_spike() -> list[dict]:
    return _do_scan("今日成交额较前5日均值放大超过2倍的ETF，规模大于3亿，按放量倍数排序取前10")


# ═══════════════════════════════════════════════
#  评分 & 排序
# ═══════════════════════════════════════════════

def _extract_code(row: dict) -> str:
    return row.get("代码", row.get("code", ""))


def _extract_name(row: dict) -> str:
    return row.get("名称", row.get("name", ""))


def _extract_num(row: dict, *keys: str) -> float:
    for k in keys:
        v = row.get(k, "")
        if v:
            cleaned = re.sub(r"[^\d.\-]", "", str(v))
            try:
                return float(cleaned)
            except ValueError:
                pass
    return 0.0


def score_and_merge(
    discount: list[dict],
    premium: list[dict],
    inflow: list[dict],
    momentum: list[dict],
    oversold: list[dict],
    volume: list[dict],
) -> list[Opportunity]:
    """合并所有扫描结果，去重，打分排序。"""
    opps: dict[str, Opportunity] = {}

    # ---- 折价机会（负溢价 = 打折） ----
    for row in discount:
        code = _extract_code(row)
        prem = _extract_num(row, "折溢价率", "溢价率")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.premium = prem
        o.price = _extract_num(row, "最新价")
        o.scale = _extract_num(row, "资产规模", "规模")
        # 折价得分：折价越大分越高
        discount_pct = abs(prem) if prem < 0 else 0
        o.score += discount_pct * 3  # 每1%折价 = 3分
        o.signals.append(f"折价 {prem:+.2f}%")

    # ---- 溢价风险（标记，不给正分） ----
    for row in premium:
        code = _extract_code(row)
        prem = _extract_num(row, "折溢价率", "溢价率")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.premium = prem
        if prem > 8:
            o.signals.append(f"⚠️ 高溢价 {prem:.1f}%，回归风险大")
            o.signal_type = "premium_alert"

    # ---- 资金流入（主力净流入 = 加分） ----
    for row in inflow:
        code = _extract_code(row)
        inflow_val = _extract_num(row, "主力净流入", "区间主力净流入资金", "净流入")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.main_inflow = inflow_val
        o.ret_1m = _extract_num(row, "近一月涨幅", "区间涨跌幅")
        # 流入得分
        if inflow_val > 1:
            o.score += min(inflow_val * 2, 10)  # 每亿流入=2分，上限10分
            o.signals.append(f"主力流入 {inflow_val:+.2f}亿")
            if not o.signal_type:
                o.signal_type = "inflow"

    # ---- 动量（近期强势 = 加分） ----
    for row in momentum:
        code = _extract_code(row)
        ret_1m = _extract_num(row, "近一月涨幅", "区间涨跌幅")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.ret_1m = ret_1m if ret_1m else o.ret_1m
        o.ret_1y = _extract_num(row, "近一年涨幅", "区间收益率") or o.ret_1y
        if ret_1m > 10:
            o.score += min(ret_1m / 5, 6)  # 每5%涨幅=1分，上限6分
            if not o.signal_type:
                o.signal_type = "momentum"

    # ---- 超跌（短期大跌 = 反弹机会？） ----
    for row in oversold:
        code = _extract_code(row)
        ret_1w = _extract_num(row, "近一周跌幅", "区间涨跌幅", "涨跌幅")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.ret_1w = ret_1w
        o.change_pct = _extract_num(row, "涨跌幅") or o.change_pct
        if ret_1w < -5:
            o.score += min(abs(ret_1w) / 5, 5)  # 每5%跌幅=1分（超跌机会）
            o.signals.append(f"近1周跌 {ret_1w:+.1f}%")
            if not o.signal_type:
                o.signal_type = "oversold"

    # ---- 放量（量能异动） ----
    for row in volume:
        code = _extract_code(row)
        vol_ratio = _extract_num(row, "量比", "放量倍数")
        if code not in opps:
            opps[code] = Opportunity(code=code)
        o = opps[code]
        o.name = o.name or _extract_name(row)
        o.volume_ratio = vol_ratio
        if vol_ratio > 2:
            o.score += 2  # 放量2倍以上=2分
            o.signals.append(f"放量 {vol_ratio:.1f}x")

    # ---- 合规：过滤掉规模太小、信号太弱的 ----
    result = []
    for o in opps.values():
        if o.scale > 0 and o.scale < 1:  # 规模<1亿的迷你ETF
            continue
        if o.score < 3 and not o.signals:  # 得分低且无信号
            continue
        result.append(o)

    result.sort(key=lambda x: x.score, reverse=True)
    return result


# ═══════════════════════════════════════════════
#  报告生成
# ═══════════════════════════════════════════════

def generate_opportunity_report(opps: list[Opportunity]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# 🔍 ETF 机会扫描日报",
        f"> 扫描时间：{now}",
        f"> 发现 {len(opps)} 个值得关注的标的",
        "",
        "---",
        "",
    ]

    # 按信号类型分组
    by_type: dict[str, list] = {}
    for o in opps:
        t = o.signal_type or "other"
        by_type.setdefault(t, []).append(o)

    type_labels = {
        "discount": "🟢 折价机会（市价低于净值）",
        "inflow": "💰 资金异动（主力大幅流入）",
        "momentum": "🚀 动量延续（近期强势）",
        "oversold": "📉 超跌反弹（短期急跌）",
        "premium_alert": "⚠️ 溢价风险（远离！）",
        "other": "📌 其他信号",
    }

    for t, label in type_labels.items():
        group = by_type.get(t, [])
        if not group:
            continue
        lines.append(f"## {label}")
        lines.append("")
        lines.append("| 代码 | 名称 | 现价 | 涨跌 | 信号 | 得分 |")
        lines.append("|------|------|------|------|------|:--:|")
        for o in group[:8]:
            signals_str = "；".join(o.signals[:3])
            change_str = f"{o.change_pct:+.2f}%" if o.change_pct else "—"
            lines.append(
                f"| {o.code} | {o.name or '—'} | {o.price:.3f} | {change_str} | {signals_str} | {o.score:.1f} |"
            )
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("### 📋 完整排名（按综合得分）")
    lines.append("")
    lines.append("| 排名 | 代码 | 名称 | 类型 | 得分 | 信号 |")
    lines.append("|:--:|------|------|------|:--:|------|")
    for i, o in enumerate(opps[:20], 1):
        signals_str = "；".join(o.signals[:2])
        type_cn = type_labels.get(o.signal_type, "综合")
        lines.append(f"| {i} | {o.code} | {o.name or '—'} | {type_cn} | {o.score:.1f} | {signals_str} |")

    lines.append("")
    lines.append("> ⚠️ 以上为算法自动扫描结果，不构成投资建议。请自行判断。")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  主流程
# ═══════════════════════════════════════════════

def run_scan() -> list[Opportunity]:
    """执行全市场扫描，返回排序后的机会列表。"""
    print("🔍 开始全市场 ETF 扫描...")
    print()

    scans = [
        ("折价机会", scan_discount_etfs),
        ("溢价风险", scan_premium_etfs),
        ("资金流入", scan_fund_inflow_etfs),
        ("动量趋势", scan_momentum_etfs),
        ("超跌反弹", scan_oversold_etfs),
        ("放量异动", scan_volume_spike),
    ]

    results = {}
    for label, func in scans:
        print(f"  ⏳ 扫描 {label}...", end=" ")
        try:
            data = func()
            print(f"找到 {len(data)} 条")
            results[label] = data
        except Exception as e:
            print(f"跳过 ({e})")
            results[label] = []

    print()
    print("📊 正在评分排序...")
    opps = score_and_merge(
        results["折价机会"],
        results["溢价风险"],
        results["资金流入"],
        results["动量趋势"],
        results["超跌反弹"],
        results["放量异动"],
    )
    print(f"✅ 共发现 {len(opps)} 个值得关注的标的")
    return opps


def main():
    opps = run_scan()
    report = generate_opportunity_report(opps)
    output = WORK_DIR / "etf_opportunities.md"
    output.write_text(report, encoding="utf-8")
    print(f"\n📄 报告已保存: {output}")
    print()
    print(report[:2000])


if __name__ == "__main__":
    main()
