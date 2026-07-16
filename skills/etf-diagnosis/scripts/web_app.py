"""
ETF 持仓诊断 — Web 界面 (Flask)
启动: python3 etf_diagnose/web_app.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, request, render_template_string
from etf_diagnose.analyzer import (
    fetch_etf_metrics,
    fetch_peer_ranking,
    fetch_macro_context,
)

app = Flask(__name__)

HTML = r"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ETF 持仓诊断</title>
<style>
  :root { --bg: #0d1117; --card: #161b22; --border: #30363d; --text: #c9d1d9; --green: #3fb950; --red: #f85149; --blue: #58a6ff; --accent: #1f6feb; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: var(--bg); color: var(--text); min-height: 100vh; }
  .container { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
  h1 { font-size: 1.6rem; margin-bottom: 4px; }
  .subtitle { color: #8b949e; margin-bottom: 24px; }
  .input-row { display: flex; gap: 10px; margin-bottom: 12px; flex-wrap: wrap; }
  .input-row input { flex: 1; min-width: 200px; padding: 10px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; }
  .input-row select { padding: 10px 14px; background: var(--card); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; }
  .btn { padding: 10px 28px; background: var(--accent); border: none; border-radius: 8px; color: #fff; font-size: 1rem; cursor: pointer; font-weight: 600; }
  .btn:hover { background: #388bfd; }
  .examples { color: #8b949e; font-size: 0.85rem; margin-bottom: 20px; }
  .examples a { color: var(--blue); text-decoration: none; cursor: pointer; }
  .card { background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 18px; margin-bottom: 16px; }
  .card h3 { margin-bottom: 12px; font-size: 1.05rem; }
  .metrics { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
  .metric { padding: 12px; background: var(--bg); border-radius: 8px; border: 1px solid var(--border); }
  .metric .label { font-size: 0.8rem; color: #8b949e; }
  .metric .value { font-size: 1.3rem; font-weight: 700; margin-top: 2px; }
  .metric .sub { font-size: 0.8rem; color: #8b949e; margin-top: 2px; }
  .green { color: var(--green); }
  .red { color: var(--red); }
  table { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid var(--border); }
  th { color: #8b949e; font-weight: 600; }
  .warning { background: rgba(248,81,73,0.1); border-left: 3px solid var(--red); padding: 10px 14px; border-radius: 0 8px 8px 0; margin: 8px 0; font-size: 0.9rem; }
  .macro { font-size: 0.9rem; line-height: 1.7; }
  .macro h3, .macro strong { color: var(--blue); }
  .spinner { display: inline-block; width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--blue); border-radius: 50%; animation: spin 0.7s linear infinite; margin-right: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading { padding: 40px; text-align: center; color: #8b949e; }
</style>
</head>
<body>
<div class="container">
  <h1>📊 ETF 持仓诊断</h1>
  <p class="subtitle">输入 ETF 代码，一键生成深度诊断报告</p>
  <form method="post" id="form">
    <div class="input-row">
      <input name="codes" value="{{ codes }}" placeholder="ETF 代码（空格或逗号分隔）" autofocus>
      <select name="category">
        {% for c in categories %}
        <option value="{{ c }}" {% if c == category %}selected{% endif %}>{{ c }}</option>
        {% endfor %}
      </select>
      <button class="btn" type="submit">🔍 开始诊断</button>
    </div>
  </form>
  <p class="examples">
    示例：
    <a onclick="fill('512480 513650')">半导体+标普500</a> ·
    <a onclick="fill('510050 159915')">上证50+创业板</a> ·
    <a onclick="fill('518880 511010')">黄金+国债</a>
  </p>

  {% if loading %}
  <div class="loading"><span class="spinner"></span> 正在拉取数据，请稍候...</div>
  {% endif %}

  {% if error %}
  <div class="card" style="border-color: var(--red);"><p class="red">❌ {{ error }}</p></div>
  {% endif %}

  {% if metrics %}
  <!-- 持仓快照 -->
  <div class="card">
    <h3>📌 持仓快照</h3>
    <div class="metrics">
      {% for m in metrics %}
      <div class="metric">
        <div class="label">{{ m.code }} {{ m.name }}</div>
        <div class="value">{{ "%.3f"|format(m.price) if m.price else "—" }}</div>
        <div class="sub {{ 'green' if m.change_pct >= 0 else 'red' }}">
          {{ "%+.2f%%"|format(m.change_pct) if m.change_pct else "—" }}
        </div>
      </div>
      {% endfor %}
    </div>
  </div>

  <!-- 核心指标 -->
  <div class="card">
    <h3>📈 核心指标对比</h3>
    <div style="overflow-x: auto;">
    <table>
      <tr><th>指标</th>{% for m in metrics %}<th>{{ m.code }}</th>{% endfor %}</tr>
      <tr><td>近1月回报</td>{% for m in metrics %}<td class="{{ 'green' if m.ret_1m > 0 else 'red' }}">{{ "%+.1f%%"|format(m.ret_1m) if m.ret_1m else "—" }}</td>{% endfor %}</tr>
      <tr><td>近3月回报</td>{% for m in metrics %}<td class="{{ 'green' if m.ret_3m > 0 else 'red' }}">{{ "%+.1f%%"|format(m.ret_3m) if m.ret_3m else "—" }}</td>{% endfor %}</tr>
      <tr><td>近1年回报</td>{% for m in metrics %}<td class="{{ 'green' if m.ret_1y > 0 else 'red' }}">{{ "%+.1f%%"|format(m.ret_1y) if m.ret_1y else "—" }}</td>{% endfor %}</tr>
      <tr><td>年化波动率</td>{% for m in metrics %}<td>{{ "%.1f%%"|format(m.volatility) if m.volatility else "—" }}</td>{% endfor %}</tr>
      <tr><td>夏普比率</td>{% for m in metrics %}<td>{{ "%.2f"|format(m.sharpe) if m.sharpe else "数据暂缺" }}</td>{% endfor %}</tr>
      <tr><td>溢价率</td>{% for m in metrics %}<td class="{{ 'red' if m.premium > 5 else '' }}">{{ "%.2f%%"|format(m.premium) if m.premium else "—" }}</td>{% endfor %}</tr>
      <tr><td>净值</td>{% for m in metrics %}<td>{{ "%.3f"|format(m.nav) if m.nav else "—" }}</td>{% endfor %}</tr>
    </table>
    </div>
  </div>

  <!-- 风险提醒 -->
  {% for m in metrics %}{% if m.warnings %}
  {% for w in m.warnings %}<div class="warning">⚠️ {{ m.code }}：{{ w }}</div>{% endfor %}
  {% endif %}{% endfor %}

  <!-- 资金流向 -->
  {% if flows %}
  <div class="card">
    <h3>💰 资金流向</h3>
    <div class="metrics">
      {% for code, flow in flows.items() %}
      <div class="metric">
        <div class="label">{{ code }} 主力净流入</div>
        <div class="value {{ 'green' if flow.get('主力净流入',0) > 0 else 'red' }}">
          {{ "%+.4f"|format(flow.get('主力净流入',0)) }} 亿
        </div>
      </div>
      {% endfor %}
    </div>
  </div>
  {% endif %}

  <!-- 同类排名 -->
  {% if peers %}
  <div class="card">
    <h3>🏆 {{ category }}类 ETF 排名（近1年）</h3>
    <div style="overflow-x: auto;">
    <table>
      {% set keys = peers[0].keys()|list %}
      <tr>{% for k in keys[:6] %}<th>{{ k }}</th>{% endfor %}</tr>
      {% for row in peers[:10] %}
      <tr>{% for k in keys[:6] %}<td>{{ row.get(k, '') }}</td>{% endfor %}</tr>
      {% endfor %}
    </table>
    </div>
  </div>
  {% endif %}

  <!-- 宏观 -->
  {% if macro %}
  <div class="card">
    <h3>🌍 宏观背景</h3>
    <div class="macro">{{ macro | safe }}</div>
  </div>
  {% endif %}

  {% endif %}
</div>

<script>
function fill(codes) { document.querySelector('input[name=codes]').value = codes; document.getElementById('form').submit(); }
</script>
</body>
</html>"""

CATEGORIES = ["半导体芯片", "消费医药", "金融地产", "新能源", "宽基指数", "债券固收", "QDII海外"]


def _simple_markdown_to_html(text: str) -> str:
    """简易 Markdown → HTML（处理粗体、标题、列表）"""
    import re
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    text = re.sub(r'^### (.+)$', r'<h4>\1</h4>', text, flags=re.MULTILINE)
    text = re.sub(r'^## (.+)$', r'<h3>\1</h3>', text, flags=re.MULTILINE)
    text = re.sub(r'^- (.+)$', r'• \1', text, flags=re.MULTILINE)
    text = re.sub(r'\n\n', '<br><br>', text)
    text = re.sub(r'\n', '<br>', text)
    return text


@app.route("/", methods=["GET", "POST"])
def index():
    codes_input = ""
    category = "半导体芯片"
    metrics = peers = macro = flows_dict = None
    error = None
    loading = False

    if request.method == "POST":
        codes_input = request.form.get("codes", "")
        category = request.form.get("category", "半导体芯片")
        loading = True

        codes = [c.strip() for c in codes_input.replace(",", " ").split() if c.strip()]
        if not codes:
            error = "请输入至少一个 ETF 代码"
            loading = False
        else:
            try:
                metrics = fetch_etf_metrics(codes)
                peers = fetch_peer_ranking(
                    f"A股{category}类ETF，按近一年收益率排名前10"
                )
                macro_raw = fetch_macro_context()
                macro = _simple_markdown_to_html(macro_raw[:3000])

                flows_dict = {}
                for m in metrics:
                    if m.main_inflow != 0:
                        flows_dict[m.code] = {"主力净流入": m.main_inflow}
                loading = False
            except Exception as e:
                error = str(e)
                loading = False

    return render_template_string(
        HTML,
        codes=codes_input,
        category=category,
        categories=CATEGORIES,
        metrics=metrics,
        peers=peers,
        macro=macro,
        flows=flows_dict,
        error=error,
        loading=loading,
    )


if __name__ == "__main__":
    print("🚀 ETF 诊断 Web 已启动 → http://127.0.0.1:5050")
    app.run(debug=False, host="127.0.0.1", port=5050)
