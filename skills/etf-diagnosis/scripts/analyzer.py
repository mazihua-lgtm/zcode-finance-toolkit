"""
ETF 持仓诊断引擎 —— 核心分析逻辑

链条：
  用户输入代码 → 拉指标 → 拉同类排名 → 拉宏观 → 生成报告
"""

import json
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ---------- 路径 ----------
SKILLS_DIR = Path.home() / ".agents" / "skills"
FINANCE_DATA = SKILLS_DIR / "mx-finance-data" / "scripts" / "get_data.py"
SCREENER = SKILLS_DIR / "mx-stocks-screener" / "scripts" / "get_data.py"
ASSISTANT = SKILLS_DIR / "mx-financial-assistant" / "scripts" / "generate_answer.py"
WORK_DIR = Path.cwd()


@dataclass
class ETFMetrics:
    code: str
    name: str = ""
    price: float = 0
    change_pct: float = 0
    ret_1m: float = 0
    ret_3m: float = 0
    ret_1y: float = 0
    sharpe: float = 0
    volatility: float = 0
    max_drawdown_1y: float = 0
    premium: float = 0
    nav: float = 0
    scale: float = 0        # 规模(亿)
    turnover: float = 0     # 换手率
    main_inflow: float = 0  # 主力净流入(亿)
    warnings: list = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    @property
    def sharpe_grade(self) -> str:
        if self.sharpe >= 0.5: return "🟢 优秀"
        if self.sharpe >= 0.3: return "🟡 一般"
        if self.sharpe >= 0.1: return "🟠 偏低"
        return "🔴 差"


# ---------- Demo 数据（API 不可用时的 fallback）----------
DEMO_METRICS = {
    "512480": {"name": "半导体ETF国联安", "price": 1.356, "change_pct": -5.62,
               "ret_1m": 29.1, "ret_3m": 73.8, "ret_1y": 163.2,
               "sharpe": 0.74, "volatility": 45.6, "max_drawdown_1y": -20.0,
               "premium": -4.74, "nav": 1.356, "scale": 233.5, "turnover": 8.57,
               "main_inflow": -3.24},
    "513650": {"name": "标普500ETF南方", "price": 1.900, "change_pct": 0.48,
               "ret_1m": 1.4, "ret_3m": 9.6, "ret_1y": 14.8,
               "sharpe": 0.38, "volatility": 13.3, "max_drawdown_1y": -10.25,
               "premium": 2.77, "nav": 1.849, "scale": 77.7, "turnover": 2.66,
               "main_inflow": -0.09},
    "511010": {"name": "国债ETF国泰", "price": 140.77, "change_pct": -0.02,
               "ret_1m": 0.13, "ret_3m": 0.85, "ret_1y": 1.89,
               "sharpe": 0.07, "volatility": 0.90, "max_drawdown_1y": -0.25,
               "premium": 0.01, "nav": 140.79, "scale": 38.1, "turnover": 0.5,
               "main_inflow": 0.01},
    "518850": {"name": "黄金ETF华夏", "price": 8.628, "change_pct": -0.53,
               "ret_1m": -4.56, "ret_3m": -15.4, "ret_1y": 16.6,
               "sharpe": 0.10, "volatility": 25.4, "max_drawdown_1y": -30.1,
               "premium": -0.04, "nav": 8.664, "scale": 147.5, "turnover": 1.8,
               "main_inflow": 0.5},
    "588710": {"name": "科创半导体设备ETF华泰柏瑞", "price": 4.319, "change_pct": 9.95,
               "ret_1m": 69.7, "ret_3m": 146.8, "ret_1y": 307.1,
               "sharpe": 0.40, "volatility": 47.4, "max_drawdown_1y": -19.6,
               "premium": 12.27, "nav": 3.847, "scale": 69.4, "turnover": 15.0,
               "main_inflow": -1.07},
}

DEMO_PEERS = [
    {"序号": "1", "代码": "588170", "名称": "科创半导体ETF华夏", "最新价": "1.214", "涨跌幅": "-6.04", "近1年": "268.5%"},
    {"序号": "2", "代码": "588710", "名称": "科创半导体设备ETF华泰柏瑞", "最新价": "3.751", "涨跌幅": "-5.85", "近1年": "266.9%"},
    {"序号": "3", "代码": "560780", "名称": "半导体设备ETF广发", "最新价": "1.273", "涨跌幅": "-7.01", "近1年": "246.3%"},
    {"序号": "4", "代码": "159516", "名称": "半导体设备ETF国泰", "最新价": "0.865", "涨跌幅": "-4.42", "近1年": "242.9%"},
    {"序号": "5", "代码": "512480", "名称": "半导体ETF国联安", "最新价": "1.356", "涨跌幅": "-5.62", "近1年": "163.2%"},
]

def _run_script(script: Path, args: list[str], timeout: int = 60) -> str:
    """运行一个 Python 脚本，返回 stdout。"""
    result = subprocess.run(
        [sys.executable, str(script)] + args,
        capture_output=True, text=True,
        timeout=timeout, cwd=str(WORK_DIR),
    )
    if result.returncode != 0:
        raise RuntimeError(f"脚本失败: {script.name}\n{result.stderr[:500]}")
    return result.stdout


def fetch_etf_metrics(codes: list[str]) -> list[ETFMetrics]:
    """批量拉取 ETF 核心指标。API 不可用时自动降级为 Demo 数据。"""
    query = "、".join(codes)
    indicators = "近1月回报、近3月回报、近1年回报、年化波动率、夏普比率、最大回撤、溢价率、单位净值、规模、换手率、主力净流入、涨跌幅"

    try:
        _run_script(FINANCE_DATA, [
            "--query", f"查询{query}的{indicators}",
            "--indicators", indicators,
        ], timeout=90)
        md_files = sorted(
            WORK_DIR.glob("miaoxiang/mx_finance_data/mx_finance_data_*.md"),
            key=lambda p: p.stat().st_mtime, reverse=True,
        )
        if md_files:
            all_metrics: dict[str, ETFMetrics] = {}
            for code in codes:
                all_metrics[code] = ETFMetrics(code=code)
            for md_file in md_files[:3]:
                partial = _parse_metrics_markdown(md_file.read_text(encoding="utf-8"), codes)
                for pm in partial:
                    _merge_metrics(all_metrics[pm.code], pm)
            if any(all_metrics[c].ret_1y == 0 for c in codes):
                raise ValueError("API 返回数据不完整")
            return list(all_metrics.values())
    except Exception as e:
        print(f"   ⚠️ API 不可用，使用 Demo 数据")

    results = []
    for code in codes:
        demo = DEMO_METRICS.get(code)
        if demo:
            m = ETFMetrics(code=code)
            for k, v in demo.items():
                setattr(m, k, v)
            results.append(m)
        else:
            results.append(ETFMetrics(code=code, name=f"ETF{code}"))
    return results


# 指标名 → ETFMetrics 字段映射（注意精确匹配优先）
_METRIC_MAP = [
    ("折溢价率", "premium"), ("溢价率", "premium"),
    ("单位净值增长率", None),   # 跳过，避免和"单位净值"混淆
    ("单位净值", "nav"),
    ("涨跌幅", "change_pct"),
    ("最新价", "price"),
    ("近1月回报", "ret_1m"),
    ("近3月回报", "ret_3m"),
    ("近1年回报", "ret_1y"),
    ("区间涨跌幅", "ret_1y"),
    ("Sharpe", "sharpe"), ("夏普比率", "sharpe"),
    ("波动率(年化)", "volatility"), ("年化波动率", "volatility"),
    ("近1月最大回撤", "max_drawdown_1m"),
    ("近3月最大回撤", "max_drawdown_3m"),
    ("近1年最大回撤", "max_drawdown_1y"),
    ("区间最大回撤(净值)", "max_drawdown_1y"),
    ("换手率", "turnover"), ("区间换手率", "turnover"),
    ("主力净流入资金", "main_inflow"), ("主力净流入", "main_inflow"),
    ("区间主力净流入资金", "main_inflow"),
    ("资产净值计算值", "scale"), ("资产规模", "scale"),
    ("区间净流入资金", "main_inflow"),
]
# 名称提取：ETF 名称通常在标题中，如 "国联安半导体ETF(512480.SH)"
_NAME_RE = re.compile(r"(.+?)\((\d+)\.(?:SH|SZ|BJ)\)")


def _extract_name_and_code(title: str) -> tuple[str, str]:
    """从标题中提取 ETF 名称和代码。如 '国联安半导体ETF(512480.SH)' → ('国联安半导体ETF', '512480')"""
    m = _NAME_RE.search(title)
    if m:
        return m.group(1).strip(), m.group(2)
    return "", ""


def _parse_metrics_markdown(content: str, codes: list[str]) -> list[ETFMetrics]:
    """
    解析 API 返回的 Markdown 表格。

    策略：
    - 每个 ## section 对应一张表
    - ## 标题中含代码的，该 section 属于此代码
    - 单实体表（表头第一列是实体名）：取指标行的第二列
    - 多实体表（表头各列是不同实体）：找对应代码的列
    - **同代码的数据累积**，后面遇到的指标覆盖前面的
    """
    result_map: dict[str, ETFMetrics] = {}
    for code in codes:
        result_map[code] = ETFMetrics(code=code)

    lines = content.split("\n")
    primary_code: str = ""          # 当前 section 所属的代码
    col_index: dict[str, int] = {}  # 多实体表：代码→列索引
    in_table: bool = False

    for i, line in enumerate(lines):
        # ## 新 section
        if line.startswith("## "):
            primary_code = ""
            col_index = {}
            in_table = False
            title = line[3:]
            name, code = _extract_name_and_code(title)
            if code and code in result_map:
                primary_code = code
                if name and not result_map[code].name:
                    result_map[code].name = name
            continue

        if not line.startswith("|"):
            in_table = False
            continue

        parts = [p.strip() for p in line.split("|") if p.strip()]
        if not parts:
            continue

        # 表头行（包含实体名(代码) 或 日期）
        if _is_header_row(parts, codes):
            in_table = True
            # 扫描各列，看哪些是目标代码
            new_cols: dict[str, int] = {}
            for idx, cell in enumerate(parts):
                _, c = _extract_name_and_code(cell)
                if c and c in result_map:
                    new_cols[c] = idx
            if len(new_cols) >= 2:
                col_index = new_cols
            elif len(new_cols) == 1:
                primary_code = list(new_cols.keys())[0]
                col_index = {}
            else:
                # 表头不含目标代码 → 跳过此表
                primary_code = ""
                col_index = {}
            continue

        if not in_table:
            continue

        # 分隔行
        if parts[0].startswith("---"):
            continue

        metric_name = parts[0]
        if _is_date(metric_name):
            continue

        # --- 多实体表：从对应列取值 ---
        if col_index:
            for code, idx in col_index.items():
                if idx < len(parts):
                    val = _clean_number(parts[idx])
                    _set_metric(result_map[code], metric_name, val)
        # --- 单实体表 ---
        elif primary_code and primary_code in result_map:
            # 跳过 "-"（无数据），取第一个有效值
            val = 0.0
            for j in range(1, len(parts)):
                candidate = _clean_number(parts[j])
                if not (isinstance(candidate, float) and candidate != candidate):  # not nan
                    val = candidate
                    break
            _set_metric(result_map[primary_code], metric_name, val)

    # 生成警告
    for m in result_map.values():
        m.warnings = []
        if m.premium > 5:
            m.warnings.append(f"溢价率 {m.premium:.1f}% 偏高，注意净值滞后或情绪过热")
        if m.premium > 10:
            m.warnings.append(f"溢价率异常高 ({m.premium:.1f}%)，存在溢价回归风险")
        if 0 < m.sharpe < 0.2:
            m.warnings.append(f"夏普比率仅 {m.sharpe:.2f}，风险调整后收益偏低")
        if m.max_drawdown_1y < -15:
            m.warnings.append(f"近1年最大回撤 {m.max_drawdown_1y:.1f}%，波动较大")

    return list(result_map.values())


def _is_header_row(parts: list[str], codes: list[str]) -> bool:
    """判断是否表头行（包含多个带代码的实体名和日期）"""
    code_count = 0
    date_count = 0
    for cell in parts:
        _, c = _extract_name_and_code(cell)
        if c:
            code_count += 1
        if _is_date(cell):
            date_count += 1
    return code_count >= 1 and (date_count >= 1 or code_count >= 2)


def _is_date(s: str) -> bool:
    """判断字符串是否为日期格式：2026-07-09 或 2026-07-09 14:23"""
    return bool(re.match(r"^\d{4}-\d{2}-\d{2}", s))


def _clean_number(s: str) -> float:
    """
    清洗数值字符串并统一转换为"亿"单位。
    '1.71亿元' → 1.71
    '10.39%' → 10.39
    '-949.8万元' → -0.09498
    '-3.237亿' → -3.237
    '-' → None（返回 sentinel）
    """
    if not s or s.strip() == "-":
        return float("nan")  # sentinel for "no data"
    s = s.strip()
    # 检测单位
    is_wan = "万" in s
    # 移除所有非数字字符（保留负号和小数点）
    cleaned = re.sub(r"[^\d.\-]", "", s)
    try:
        val = float(cleaned) if cleaned else float("nan")
    except ValueError:
        return float("nan")
    if is_wan:
        val = val / 10000  # 万元 → 亿元
    return val


def _set_metric(m: ETFMetrics, metric_name: str, value: float):
    """根据指标名设置 ETFMetrics 对应字段。跳过 nan 值和被标记为 None 的字段。"""
    import math
    if math.isnan(value):
        return
    field = None
    for key, f in _METRIC_MAP:
        if key == metric_name:
            field = f
            break
    if field is None:
        # 模糊匹配（仅当精确匹配失败时）
        for key, f in _METRIC_MAP:
            if key in metric_name:
                field = f
                break
    if field is None:
        return  # 无法匹配的指标，跳过
    if value == 0.0:
        return
    current = getattr(m, field, 0)
    if current == 0.0 or abs(value) > 0:
        setattr(m, field, value)


def _merge_metrics(target: ETFMetrics, source: ETFMetrics):
    """将 source 中的非零/非默认值合并到 target。"""
    for field_name in [
        "name", "price", "change_pct", "ret_1m", "ret_3m", "ret_1y",
        "sharpe", "volatility", "max_drawdown_1y", "max_drawdown_1m",
        "max_drawdown_3m", "premium", "nav", "scale", "turnover",
        "main_inflow",
    ]:
        src_val = getattr(source, field_name, 0)
        tgt_val = getattr(target, field_name, 0)
        if isinstance(src_val, str) and src_val:
            if not tgt_val:
                setattr(target, field_name, src_val)
        elif isinstance(src_val, (int, float)) and src_val != 0:
            if tgt_val == 0:
                setattr(target, field_name, src_val)


def fetch_peer_ranking(query: str, select_type: str = "ETF") -> list[dict]:
    """获取同类 ETF 排名。"""
    _run_script(SCREENER, [
        "--query", query,
        "--select-type", select_type,
    ], timeout=60)

    csv_files = sorted(
        WORK_DIR.glob("miaoxiang/mx_stocks_screener/mx_stocks_screener_*.csv"),
        key=lambda p: p.stat().st_mtime, reverse=True,
    )
    if not csv_files:
        return []

    import csv
    rows = []
    with open(csv_files[0], encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def fetch_macro_context(question: str = "近期影响A股和美股的宏观经济要点、通胀、利率趋势") -> str:
    """拉宏观背景摘要。"""
    output = _run_script(ASSISTANT, ["--query", question], timeout=60)
    try:
        data = json.loads(output)
        return data.get("answer", output[:2000])
    except json.JSONDecodeError:
        return output[:2000]


def fetch_fund_flows(codes: list[str]) -> dict:
    """拉资金流向（复用主查询结果，节省一次 API 调用）。"""
    # 不再单独查询，直接从主指标查询结果中提取
    # 这里返回空 dict，资金流向已在 _parse_metrics_markdown 中提取
    return {}
