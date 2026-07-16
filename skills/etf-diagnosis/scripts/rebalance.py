"""
ETF 调仓算法引擎 —— 多种优化策略对比

算法：
  1. 风险平价（Risk Parity）—— 各资产风险贡献相等
  2. 最大夏普（Max Sharpe）  —— 最大化风险调整后收益
  3. 最小方差（Min Variance）—— 最小化组合波动率
  4. 等权重（Equal Weight）  —— 基准对照
"""

import math
import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class RebalanceResult:
    """单个算法的调仓结果"""
    algorithm: str           # 算法名称
    weights: dict[str, float]  # 代码 → 目标权重
    expected_return: float   # 预期年化收益
    expected_volatility: float  # 预期年化波动
    sharpe: float            # 预期夏普
    description: str         # 一句话解释


@dataclass
class RebalanceReport:
    """多算法对比 + 当前持仓"""
    current_weights: dict[str, float]
    current_total: float     # 总资产
    risk_free_rate: float
    results: list[RebalanceResult]
    best: str                # 最优算法名称
    trade_instructions: str  # 可执行的调仓指令


def _clean_returns(returns: dict[str, list[float]]) -> tuple[np.ndarray, list[str]]:
    """将历史收益字典转为对齐的 numpy 矩阵（行=日期，列=资产）。"""
    codes = list(returns.keys())
    min_len = min(len(v) for v in returns.values())
    matrix = np.array([returns[c][:min_len] for c in codes]).T  # T x N
    return matrix, codes


def _annualize(daily_returns: np.ndarray, periods: int = 252) -> tuple[np.ndarray, np.ndarray]:
    """从日收益计算年化收益率和协方差矩阵。"""
    mu = daily_returns.mean(axis=0) * periods
    sigma = np.cov(daily_returns, rowvar=False) * periods
    return mu, sigma


# ═══════════════════════════════════════════════
#  算法 1：风险平价 (Risk Parity)
# ═══════════════════════════════════════════════

def risk_parity(sigma: np.ndarray, max_iter: int = 1000, tol: float = 1e-8) -> np.ndarray:
    """
    风险平价优化。
    目标：各资产的风险贡献 (w_i * (Σw)_i) 相等。
    使用 Newton-Raphson 迭代求解。
    """
    n = sigma.shape[0]
    w = np.ones(n) / n  # 从等权重开始

    for _ in range(max_iter):
        sigma_w = sigma @ w
        port_vol = math.sqrt(w @ sigma_w)
        # 风险贡献
        rc = w * sigma_w / port_vol
        # 目标：rc 的方差最小
        target_rc = port_vol / n
        grad = 2 * (rc - target_rc) / port_vol

        if np.max(np.abs(grad)) < tol:
            break

        # 简单梯度下降
        step = 0.01
        w = w - step * grad
        w = np.maximum(w, 1e-8)
        w = w / w.sum()

    return w


# ═══════════════════════════════════════════════
#  算法 2：最大夏普 (Max Sharpe)
# ═══════════════════════════════════════════════

def max_sharpe(mu: np.ndarray, sigma: np.ndarray, rf: float = 0.02, max_weight: float = 0.40) -> np.ndarray:
    """
    最大化夏普比率（带单资产权重上限）。
    max (w·μ - rf) / √(w·Σ·w)
    """
    n = len(mu)
    excess = mu - rf

    # 使用 Ledoit-Wolf 收缩估计提高稳健性
    try:
        # 简单收缩：向等相关系数矩阵收缩
        rho_avg = 0.3  # 平均相关系数
        diag = np.diag(np.diag(sigma))
        off_diag = np.outer(np.sqrt(np.diag(sigma)), np.sqrt(np.diag(sigma))) * rho_avg
        np.fill_diagonal(off_diag, 0)
        sigma_shrunk = 0.5 * sigma + 0.5 * (diag + off_diag)
    except Exception:
        sigma_shrunk = sigma

    try:
        sigma_inv = np.linalg.inv(sigma_shrunk)
    except np.linalg.LinAlgError:
        sigma_inv = np.linalg.pinv(sigma_shrunk)

    w = sigma_inv @ excess
    w = np.maximum(w, 0)  # 禁止做空
    if w.sum() > 0:
        w = w / w.sum()
    else:
        w = np.ones(n) / n

    # 裁剪单资产上限
    w = np.minimum(w, max_weight)
    w = w / w.sum()

    return w


# ═══════════════════════════════════════════════
#  算法 3：最小方差 (Min Variance)
# ═══════════════════════════════════════════════

def min_variance(sigma: np.ndarray) -> np.ndarray:
    """
    最小化组合方差。
    解析解：w* = Σ⁻¹·1 / 1ᵀ·Σ⁻¹·1
    """
    n = sigma.shape[0]
    ones = np.ones(n)
    try:
        sigma_inv = np.linalg.inv(sigma)
    except np.linalg.LinAlgError:
        sigma_inv = np.linalg.pinv(sigma)

    w = sigma_inv @ ones
    w = np.maximum(w, 0)
    if w.sum() > 0:
        w = w / w.sum()
    else:
        w = ones / n
    return w


# ═══════════════════════════════════════════════
#  引擎：综合调用 + 生成报告
# ═══════════════════════════════════════════════

def run_rebalance(
    current_holdings: dict[str, float],  # 代码 → 市值
    returns: dict[str, list[float]],      # 代码 → 日收益率序列
    total_cash: float = 0,
    risk_free_rate: float = 0.02,
    codes: Optional[list[str]] = None,
) -> RebalanceReport:
    """
    主入口：运行所有算法，对比，生成调仓指令。
    """
    codes_list = codes or list(current_holdings.keys())
    if not codes_list:
        raise ValueError("需要至少一只 ETF")

    # 对齐数据
    ret_matrix, ret_codes = _clean_returns(returns)
    if ret_matrix.shape[1] < len(codes_list):
        # 某些代码没有收益数据，只用有的
        codes_list = [c for c in codes_list if c in ret_codes]
        if not codes_list:
            raise ValueError("所有 ETF 均无历史收益数据")

    # 重建索引
    idx_map = {c: i for i, c in enumerate(ret_codes)}
    indices = [idx_map[c] for c in codes_list]
    ret_sub = ret_matrix[:, indices]

    mu, sigma = _annualize(ret_sub)

    total = sum(current_holdings.get(c, 0) for c in codes_list) + total_cash
    current_weights = {c: current_holdings.get(c, 0) / total for c in codes_list}
    current_weights["现金"] = total_cash / total if total_cash > 0 else 0

    results: list[RebalanceResult] = []

    # 等权重基准
    eq_w = np.ones(len(codes_list)) / len(codes_list)
    eq_ret = eq_w @ mu
    eq_vol = math.sqrt(eq_w @ sigma @ eq_w)
    results.append(RebalanceResult(
        algorithm="等权重（基准）",
        weights={c: eq_w[i] for i, c in enumerate(codes_list)},
        expected_return=eq_ret,
        expected_volatility=eq_vol,
        sharpe=(eq_ret - risk_free_rate) / eq_vol if eq_vol > 0 else 0,
        description="各资产平均分配，最简单的对照策略",
    ))

    # 风险平价
    try:
        rp_w = risk_parity(sigma)
        rp_ret = rp_w @ mu
        rp_vol = math.sqrt(rp_w @ sigma @ rp_w)
        results.append(RebalanceResult(
            algorithm="风险平价",
            weights={c: rp_w[i] for i, c in enumerate(codes_list)},
            expected_return=rp_ret,
            expected_volatility=rp_vol,
            sharpe=(rp_ret - risk_free_rate) / rp_vol if rp_vol > 0 else 0,
            description="各资产风险贡献相等，防御性最强，适合震荡市",
        ))
    except Exception:
        pass

    # 最大夏普
    try:
        ms_w = max_sharpe(mu, sigma, risk_free_rate)
        ms_ret = ms_w @ mu
        ms_vol = math.sqrt(ms_w @ sigma @ ms_w)
        results.append(RebalanceResult(
            algorithm="最大夏普",
            weights={c: ms_w[i] for i, c in enumerate(codes_list)},
            expected_return=ms_ret,
            expected_volatility=ms_vol,
            sharpe=(ms_ret - risk_free_rate) / ms_vol if ms_vol > 0 else 0,
            description="最大化每单位风险的收益，历史表现最优的配置",
        ))
    except Exception:
        pass

    # 最小方差
    try:
        mv_w = min_variance(sigma)
        mv_ret = mv_w @ mu
        mv_vol = math.sqrt(mv_w @ sigma @ mv_w)
        results.append(RebalanceResult(
            algorithm="最小方差",
            weights={c: mv_w[i] for i, c in enumerate(codes_list)},
            expected_return=mv_ret,
            expected_volatility=mv_vol,
            sharpe=(mv_ret - risk_free_rate) / mv_vol if mv_vol > 0 else 0,
            description="最小化整体波动，最保守的策略",
        ))
    except Exception:
        pass

    # 最优算法
    best = max(results, key=lambda r: r.sharpe)

    # 生成调仓指令
    trade_lines = _generate_trades(current_weights, best.weights, total, current_holdings)

    return RebalanceReport(
        current_weights=current_weights,
        current_total=total,
        risk_free_rate=risk_free_rate,
        results=results,
        best=best.algorithm,
        trade_instructions=trade_lines,
    )


def _generate_trades(
    current: dict[str, float],
    target: dict[str, float],
    total: float,
    holdings: dict[str, float],
) -> str:
    """生成可执行的调仓指令文本。"""
    lines: list[str] = []

    for code in set(list(current.keys()) + list(target.keys())):
        if code == "现金":
            continue
        curr_w = current.get(code, 0)
        tgt_w = target.get(code, 0)
        curr_val = curr_w * total
        tgt_val = tgt_w * total
        diff = tgt_val - curr_val

        if abs(diff) < total * 0.01:  # 变动 <1%，忽略
            continue

        name = code
        action = "🟢 买入" if diff > 0 else "🔴 卖出"
        lines.append(
            f"| {code} | {curr_w*100:.1f}% → {tgt_w*100:.1f}% | "
            f"{action} ¥{abs(diff):,.0f} |"
        )

    if lines:
        return (
            "| 代码 | 当前 → 目标 | 操作 |\n"
            "|------|------------|------|\n"
            + "\n".join(lines)
        )
    return "✅ 当前配置已接近最优，无需调整。"


# ═══════════════════════════════════════════════
#  报告渲染
# ═══════════════════════════════════════════════

def format_report(report: RebalanceReport) -> str:
    """生成 Markdown 格式的完整调仓报告。"""
    lines = [
        "# 📐 ETF 调仓分析",
        "",
        f"**总资产**：¥{report.current_total:,.0f}　|　**无风险利率**：{report.risk_free_rate*100:.1f}%",
        "",
        "---",
        "",
        "## 🏋️ 多算法对比",
        "",
        "| 算法 | 预期年化收益 | 预期年化波动 | 预期夏普 | 逻辑 |",
        "|------|:----------:|:----------:|:------:|------|",
    ]

    for r in report.results:
        best_mark = " ⭐" if r.algorithm == report.best else ""
        lines.append(
            f"| **{r.algorithm}**{best_mark} | {r.expected_return*100:.1f}% | "
            f"{r.expected_volatility*100:.1f}% | {r.sharpe:.2f} | {r.description} |"
        )

    lines.append("")
    lines.append(f"🏆 **最优策略**：{report.best}（夏普 {max(r.sharpe for r in report.results):.2f}）")
    lines.append("")

    # 权重对比
    lines.append("## ⚖️ 权重对比")
    lines.append("")

    all_codes = list(report.current_weights.keys())
    header = "| 资产 | 当前 | " + " | ".join(r.algorithm for r in report.results) + " |"
    sep = "|------|:----:|" + ":----:|" * len(report.results) + "|"
    lines.append(header)
    lines.append(sep)

    for code in all_codes:
        row = f"| {code} | {report.current_weights.get(code,0)*100:.0f}% |"
        for r in report.results:
            row += f" {r.weights.get(code,0)*100:.0f}% |"
        lines.append(row)

    lines.append("")

    # 调仓指令
    lines.append("## 📋 调仓指令")
    lines.append("")
    lines.append(f"按 **{report.best}** 策略：")
    lines.append("")
    lines.append(report.trade_instructions)
    lines.append("")
    lines.append("> ⚠️ 以上基于历史/模拟数据的最优配置，不构成投资建议。过往表现不代表未来。")
    lines.append("> 💡 API 积分恢复后可使用真实历史收益数据，结果将更可靠。")

    return "\n".join(lines)
