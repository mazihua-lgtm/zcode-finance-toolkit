"""
CodeGraph —— 项目代码知识图谱

扫描项目 → 提取结构 → 构建关系图 → 自然语言查询
支持：Python, JavaScript/TypeScript, SQL/Prisma
"""

import ast
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Optional

STORAGE = Path.home() / ".zcode" / "codegraph"
INDEX_FILE = "codegraph_index.json"

SKIP_DIRS = {
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    ".next", "dist", "build", ".zcode", "miaoxiang",
    ".DS_Store", ".npm", ".cache", "etf_diagnose_report.md",
    "etf_opportunities.md", "changeguard_report.md",
}


# ═══════════════════════════════════════════════
#  扫描器
# ═══════════════════════════════════════════════

def scan(root: Optional[Path] = None) -> dict:
    """扫描项目，构建代码索引。"""
    root = root or Path.cwd()
    index = {
        "root": str(root),
        "files": {},
        "functions": [],
        "classes": [],
        "imports": [],
        "api_routes": [],
        "db_tables": [],
        "exports": [],
    }

    for filepath in root.rglob("*"):
        if not filepath.is_file():
            continue
        rel = str(filepath.relative_to(root))
        if any(skip in rel.split("/") for skip in SKIP_DIRS):
            continue

        suffix = filepath.suffix.lower()
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        index["files"][rel] = {
            "size": filepath.stat().st_size,
            "lines": content.count("\n"),
        }

        if suffix == ".py":
            _parse_python(rel, content, index)
        elif suffix in (".js", ".ts", ".jsx", ".tsx"):
            _parse_javascript(rel, content, index)
        elif suffix in (".sql", ".prisma"):
            _parse_sql(rel, content, index)

    # 构建关系
    index["relations"] = _build_relations(index)

    # 存储
    STORAGE.mkdir(parents=True, exist_ok=True)
    out = STORAGE / INDEX_FILE
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2))

    return index


# ═══════════════════════════════════════════════
#  解析器
# ═══════════════════════════════════════════════

def _parse_python(rel: str, content: str, index: dict):
    """解析 Python 文件。"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        # fallback regex
        _parse_python_regex(rel, content, index)
        return

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            index["functions"].append({
                "name": node.name,
                "file": rel,
                "line": node.lineno,
                "language": "python",
            })
        elif isinstance(node, ast.ClassDef):
            index["classes"].append({
                "name": node.name,
                "file": rel,
                "line": node.lineno,
                "language": "python",
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                index["imports"].append({
                    "from": rel,
                    "import": alias.name,
                    "type": "python_import",
                })
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for alias in node.names:
                    index["imports"].append({
                        "from": rel,
                        "import": f"{node.module}.{alias.name}",
                        "type": "python_import",
                    })


def _parse_python_regex(rel: str, content: str, index: dict):
    """Regex fallback for broken Python files."""
    for m in re.finditer(r"^def\s+(\w+)", content, re.MULTILINE):
        index["functions"].append({
            "name": m.group(1), "file": rel, "line": 0, "language": "python",
        })
    for m in re.finditer(r"^class\s+(\w+)", content, re.MULTILINE):
        index["classes"].append({
            "name": m.group(1), "file": rel, "line": 0, "language": "python",
        })


def _parse_javascript(rel: str, content: str, index: dict):
    """解析 JS/TS 文件。"""
    # 函数
    for m in re.finditer(
        r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", content
    ):
        index["functions"].append({
            "name": m.group(1), "file": rel, "line": 0, "language": "javascript",
        })
    # 箭头函数（导出的）
    for m in re.finditer(r"export\s+(?:const|let|var)\s+(\w+)\s*=", content):
        index["functions"].append({
            "name": m.group(1), "file": rel, "line": 0, "language": "javascript",
        })
    # 类
    for m in re.finditer(r"class\s+(\w+)", content):
        index["classes"].append({
            "name": m.group(1), "file": rel, "line": 0, "language": "javascript",
        })
    # import
    for m in re.finditer(r"import\s+.*?\s+from\s+['\"](.+?)['\"]", content):
        index["imports"].append({
            "from": rel, "import": m.group(1), "type": "js_import",
        })
    # API routes (Next.js / Express)
    for m in re.finditer(
        r"(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*['\"](/[^'\"]*)",
        content, re.IGNORECASE,
    ):
        index["api_routes"].append({
            "method": "GET/POST",
            "path": m.group(1),
            "file": rel,
        })
    # Flask/FastAPI routes
    for m in re.finditer(r"@(?:app|router)\.(?:get|post|put|delete|patch)\s*\(\s*['\"](/[^'\"]*)", content):
        index["api_routes"].append({
            "method": m.group(1).upper(),
            "path": m.group(2),
            "file": rel,
        })


def _parse_sql(rel: str, content: str, index: dict):
    """解析 SQL/Prisma 文件。"""
    # CREATE TABLE
    for m in re.finditer(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)", content, re.IGNORECASE):
        index["db_tables"].append({"name": m.group(1), "file": rel})
    # Prisma model
    for m in re.finditer(r"model\s+(\w+)\s*\{", content):
        index["db_tables"].append({"name": m.group(1), "file": rel})


# ═══════════════════════════════════════════════
#  关系图谱
# ═══════════════════════════════════════════════

def _build_relations(index: dict) -> dict:
    """从已解析的结构中构建关系。"""
    rels = {"file_deps": defaultdict(set), "imports_by_module": defaultdict(list)}

    for imp in index["imports"]:
        # 本地文件导入
        imported = imp["import"]
        src_file = imp["from"]
        if imported.startswith("."):
            rels["file_deps"][src_file].add(imported)
        else:
            mod = imported.split(".")[0]
            rels["imports_by_module"][mod].append(src_file)

    # 转为可序列化格式
    return {
        "file_deps": {k: list(v) for k, v in rels["file_deps"].items()},
        "imports_by_module": dict(rels["imports_by_module"]),
    }


# ═══════════════════════════════════════════════
#  查询引擎
# ═══════════════════════════════════════════════

def load_index() -> Optional[dict]:
    """加载最近的索引。"""
    idx = STORAGE / INDEX_FILE
    if idx.exists():
        return json.loads(idx.read_text())
    return None


def query(q: str) -> str:
    """自然语言查询代码库。"""
    index = load_index()
    if not index:
        return "📭 尚未扫描项目。请先运行 `python3 codegraph.py scan`。"

    q_lower = q.lower()
    results = []
    # 提取可能的关键词（去掉常见疑问词）
    search_term = q_lower
    category_keywords = ["函数", "function", "func", "方法", "def", "类", "class", "模块",
                         "api", "路由", "route", "接口", "endpoint", "表", "数据库", "db",
                         "table", "schema", "model", "文件", "file"]
    for prefix in ["有哪些", "列出", "显示", "找出", "查找", "搜索", "所有", "find", "list", "show", "all"]:
        if search_term.startswith(prefix):
            search_term = search_term[len(prefix):].strip()
            break
    # 如果提取后的词本身是类别关键词，则清空（表示列出全部）
    if search_term in category_keywords:
        search_term = ""

    def _add_funcs(filter_term=""):
        for f in index.get("functions", []):
            if not filter_term or _match(filter_term, f["name"]):
                results.append(f"🔧 `{f['name']}()` → `{f['file']}`")

    def _add_classes(filter_term=""):
        for c in index.get("classes", []):
            if not filter_term or _match(filter_term, c["name"]):
                results.append(f"📦 `{c['name']}` → `{c['file']}`")

    def _add_routes(filter_term=""):
        for r in index.get("api_routes", []):
            if not filter_term or _match(filter_term, r["path"]):
                results.append(f"🌐 `{r['method']} {r['path']}` → `{r['file']}`")

    def _add_tables(filter_term=""):
        for t in index.get("db_tables", []):
            if not filter_term or _match(filter_term, t["name"]):
                results.append(f"🗄️ `{t['name']}` → `{t['file']}`")

    def _add_files(filter_term=""):
        for rel in index.get("files", {}):
            if not filter_term or _match(filter_term, rel):
                results.append(f"📄 `{rel}`")

    # 类别匹配
    if any(kw in q_lower for kw in ["函数", "function", "func", "方法", "def"]):
        _add_funcs(search_term if search_term != q_lower else "")
    elif any(kw in q_lower for kw in ["类", "class", "模块"]):
        _add_classes(search_term if search_term != q_lower else "")
    elif any(kw in q_lower for kw in ["api", "路由", "route", "接口", "endpoint"]):
        _add_routes(search_term if search_term != q_lower else "")
    elif any(kw in q_lower for kw in ["表", "数据库", "db", "table", "schema", "model"]):
        _add_tables(search_term if search_term != q_lower else "")
    elif any(kw in q_lower for kw in ["文件", "file"]):
        _add_files(search_term if search_term != q_lower else "")
    else:
        # 通用搜索：全字段
        _add_funcs(search_term)
        _add_classes(search_term)
        _add_routes(search_term)
        _add_tables(search_term)
        _add_files(search_term)

    if not results:
        return (
            f"🔍 未找到与「{q}」相关的结果。\n\n"
            f"试试：\n"
            f"• 列出所有函数\n"
            f"• 有哪些API接口\n"
            f"• 数据库表\n"
            f"• 包含 auth 的文件"
        )

    return "\n".join(results[:25])


def _match(query: str, target: str) -> bool:
    """模糊匹配。"""
    target_lower = target.lower()
    # 精确匹配
    if query in target_lower:
        return True
    # 单词匹配
    for word in query.split():
        if len(word) >= 2 and word in target_lower:
            return True
    return False


# ═══════════════════════════════════════════════
#  报告
# ═══════════════════════════════════════════════

def summary(index: Optional[dict] = None) -> str:
    """生成项目摘要。"""
    idx = index or load_index()
    if not idx:
        return "📭 尚未扫描。"

    files = idx.get("files", {})
    total_lines = sum(f.get("lines", 0) for f in files.values())
    total_size = sum(f.get("size", 0) for f in files.values())

    lines = [
        "# 📊 项目代码图谱",
        "",
        f"**根目录**：`{idx['root']}`",
        "",
        "| 指标 | 数值 |",
        "|------|------|",
        f"| 文件数 | {len(files)} |",
        f"| 总行数 | {total_lines:,} |",
        f"| 总大小 | {total_size / 1024:.0f} KB |",
        f"| 函数 | {len(idx.get('functions',[]))} |",
        f"| 类 | {len(idx.get('classes',[]))} |",
        f"| API 路由 | {len(idx.get('api_routes',[]))} |",
        f"| 数据库表 | {len(idx.get('db_tables',[]))} |",
        "",
        "## 🔗 文件依赖 Top 5",
    ]

    deps = idx.get("relations", {}).get("file_deps", {})
    top_deps = sorted(deps.items(), key=lambda x: len(x[1]), reverse=True)[:5]
    for f, deps_list in top_deps:
        lines.append(f"- **{f}** → {len(deps_list)} 个依赖")

    lines.append("")
    lines.append("## 🌐 API 路由")
    for r in idx.get("api_routes", [])[:15]:
        lines.append(f"- `{r['method']} {r['path']}` → `{r['file']}`")

    lines.append("")
    lines.append("## 🗄️ 数据库表")
    for t in idx.get("db_tables", []):
        lines.append(f"- `{t['name']}` → `{t['file']}`")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"

    if cmd == "scan":
        root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()
        idx = scan(root)
        print(summary(idx))

    elif cmd == "report":
        print(summary())

    elif cmd == "query" and len(sys.argv) > 2:
        print(query(" ".join(sys.argv[2:])))

    else:
        print("用法: codegraph [scan|report|query <问题>]")


if __name__ == "__main__":
    main()
