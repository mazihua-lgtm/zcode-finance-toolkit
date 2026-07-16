"""
ChangeGuard —— AI 变更追踪 + 风险审查

工作流：
  1. SessionStart → 快照所有文件哈希
  2. 随时调用 → 对比变化，标记风险
  3. 输出审查报告
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

STORAGE = Path.home() / ".zcode" / "changeguard"
SNAPSHOT_FILE = STORAGE / "snapshot.json"
HISTORY_FILE = STORAGE / "history.json"

# 忽略的目录/文件模式
IGNORE_PATTERNS = [
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".DS_Store", "*.pyc", ".next", "dist", "build",
    ".zcode", "miaoxiang", "etf_diagnose_report.md",
    "etf_opportunities.md", ".npm", ".cache",
]

# 高风险文件模式
HIGH_RISK_PATTERNS = [
    (r"\.env$", "🔴 环境变量文件"),
    (r"\.env\..*", "🔴 环境配置"),
    (r"package\.json$", "🟡 依赖配置"),
    (r"prisma/.*\.prisma$", "🟡 数据库 Schema"),
    (r"docker.*\.yml$", "🟡 Docker 配置"),
    (r"\.sh$", "🟡 Shell 脚本"),
    (r"Makefile$", "🟡 构建脚本"),
    (r"config.*\.json$", "🟡 配置文件"),
]

# 风险内容检测
RISK_CONTENT = [
    (r'(?:api[_-]?key|apikey|secret|token|password)\s*[=:]\s*["\']?[a-zA-Z0-9_\-]{16,}["\']?',
     "🔴 疑似密钥/密码泄露"),
    (r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----',
     "🔴 私钥泄露"),
    (r'sk-[a-zA-Z0-9_\-]{20,}',
     "🔴 OpenAI/Claude API Key"),
]


# ═══════════════════════════════════════════════
#  快照引擎
# ═══════════════════════════════════════════════

def _should_ignore(path: Path, root: Path) -> bool:
    rel = str(path.relative_to(root))
    for pat in IGNORE_PATTERNS:
        if pat.startswith("*"):
            if path.match(pat):
                return True
        elif pat in rel or rel.startswith(pat + "/"):
            return True
    return False


def _hash_file(path: Path) -> str:
    try:
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except Exception:
        return "ERROR"


def snapshot(root: Optional[Path] = None) -> dict:
    """创建当前工作目录的文件快照。"""
    root = root or Path.cwd()
    files = {}
    for p in root.rglob("*"):
        if p.is_file() and not _should_ignore(p, root):
            rel = str(p.relative_to(root))
            files[rel] = {
                "hash": _hash_file(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }
    snap = {
        "root": str(root),
        "time": datetime.now().isoformat(),
        "files": files,
    }
    STORAGE.mkdir(parents=True, exist_ok=True)
    SNAPSHOT_FILE.write_text(json.dumps(snap, ensure_ascii=False, indent=2))
    return snap


def load_snapshot() -> Optional[dict]:
    """加载最近的快照。"""
    if SNAPSHOT_FILE.exists():
        return json.loads(SNAPSHOT_FILE.read_text())
    return None


# ═══════════════════════════════════════════════
#  变更检测
# ═══════════════════════════════════════════════

def detect_changes(root: Optional[Path] = None) -> dict:
    """对比快照和当前状态，返回变更列表。"""
    root = root or Path.cwd()
    snap = load_snapshot()
    if not snap:
        return {"error": "请先运行 snapshot 创建快照"}

    old_files = snap["files"]
    new_files = {}

    for p in root.rglob("*"):
        if p.is_file() and not _should_ignore(p, root):
            rel = str(p.relative_to(root))
            new_files[rel] = {
                "hash": _hash_file(p),
                "size": p.stat().st_size,
                "mtime": p.stat().st_mtime,
            }

    added = set(new_files.keys()) - set(old_files.keys())
    removed = set(old_files.keys()) - set(new_files.keys())
    changed = []
    for rel in set(old_files.keys()) & set(new_files.keys()):
        if old_files[rel]["hash"] != new_files[rel]["hash"]:
            changed.append({
                "file": rel,
                "old_size": old_files[rel]["size"],
                "new_size": new_files[rel]["size"],
                "delta": new_files[rel]["size"] - old_files[rel]["size"],
            })

    # 检测删除行数多的文件
    big_deletes = []
    for rel in removed:
        old_size = old_files[rel]["size"]
        if old_size > 1000:  # >1KB
            big_deletes.append({"file": rel, "old_size": old_size})

    return {
        "added": sorted(added),
        "removed": sorted(removed),
        "changed": sorted(changed, key=lambda c: abs(c["delta"]), reverse=True),
        "big_deletes": big_deletes,
        "total_files": len(new_files),
        "snapshot_time": snap["time"],
    }


# ═══════════════════════════════════════════════
#  风险检测
# ═══════════════════════════════════════════════

def detect_risks(root: Optional[Path] = None) -> list[dict]:
    """扫描变更文件中的风险内容。"""
    root = root or Path.cwd()
    changes = detect_changes(root)
    risks = []

    # 高风险文件类型
    all_changed = set(c["file"] for c in changes.get("changed", []))
    all_changed.update(changes.get("added", []))
    all_changed.update(changes.get("removed", []))

    for rel in all_changed:
        filepath = root / rel
        if not filepath.exists():
            continue
        for pattern, label in HIGH_RISK_PATTERNS:
            if re.search(pattern, rel):
                risks.append({"file": rel, "risk": label, "level": "high"})
                break

    # 大文件删除
    for d in changes.get("big_deletes", []):
        risks.append({
            "file": d["file"],
            "risk": f"🔴 删除大文件（{d['old_size']:,}字节）",
            "level": "critical"
        })

    # 内容风险扫描（仅文本文件）
    for rel in all_changed:
        filepath = root / rel
        if not filepath.exists() or filepath.stat().st_size > 50000:
            continue
        try:
            content = filepath.read_text(encoding="utf-8", errors="ignore")
            for pattern, label in RISK_CONTENT:
                if re.search(pattern, content, re.IGNORECASE):
                    risks.append({"file": rel, "risk": label, "level": "critical"})
                    break
        except Exception:
            pass

    return risks


# ═══════════════════════════════════════════════
#  报告
# ═══════════════════════════════════════════════

def generate_report(root: Optional[Path] = None) -> str:
    """生成完整的变更审查报告。"""
    root = root or Path.cwd()
    changes = detect_changes(root)
    risks = detect_risks(root)

    if "error" in changes:
        return f"❌ {changes['error']}"

    lines = [
        "# 🔍 AI 变更审查报告",
        "",
        f"**快照时间**：{changes['snapshot_time']}",
        f"**检查时间**：{datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**文件总数**：{changes['total_files']}",
        "",
    ]

    # 摘要
    added_n = len(changes["added"])
    removed_n = len(changes["removed"])
    changed_n = len(changes["changed"])
    risk_n = len(risks)

    lines.append("## 📊 变更摘要")
    lines.append(f"- 🟢 新增：{added_n} 个文件")
    lines.append(f"- 🔴 删除：{removed_n} 个文件")
    lines.append(f"- 🟡 修改：{changed_n} 个文件")
    if risk_n > 0:
        lines.append(f"- ⚠️ 风险项：**{risk_n}** 个")
    lines.append("")

    # 风险（优先展示）
    if risks:
        lines.append("## ⚠️ 风险警告")
        lines.append("")
        for r in risks:
            lines.append(f"- {r['risk']}：`{r['file']}`")
        lines.append("")

    # 高风险文件
    if changes["big_deletes"]:
        lines.append("## 🔴 大文件删除")
        for d in changes["big_deletes"]:
            lines.append(f"- `{d['file']}` ({d['old_size']:,} 字节)")
        lines.append("")

    # 修改详情
    if changes["changed"]:
        lines.append("## 📝 文件修改（按变动大小排序）")
        lines.append("")
        for c in changes["changed"][:15]:
            sign = "+" if c["delta"] >= 0 else ""
            lines.append(f"- `{c['file']}` ({c['old_size']:,} → {c['new_size']:,}, {sign}{c['delta']:,} 字节)")
        if len(changes["changed"]) > 15:
            lines.append(f"- ... 还有 {len(changes['changed']) - 15} 个文件")
        lines.append("")

    # 新增文件
    if changes["added"]:
        lines.append(f"## 🟢 新增文件（{len(changes['added'])}）")
        lines.append("")
        for f in changes["added"][:10]:
            lines.append(f"- `{f}`")
        if len(changes["added"]) > 10:
            lines.append(f"- ... 还有 {len(changes['added']) - 10} 个")
        lines.append("")

    # 安全结论
    if risk_n == 0:
        lines.append("## ✅ 安全结论")
        lines.append("未检测到风险项。所有变更看起来正常。")
    else:
        lines.append("## ⚠️ 需要人工审查")
        lines.append(f"发现 {risk_n} 个风险项，请在合并前逐条检查。")

    return "\n".join(lines)


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

def main():
    if len(sys.argv) < 2:
        print("用法: changeguard [snapshot|check|report]")
        return

    cmd = sys.argv[1]
    root = Path(sys.argv[2]) if len(sys.argv) > 2 else Path.cwd()

    if cmd == "snapshot":
        snap = snapshot(root)
        print(f"✅ 已快照 {len(snap['files'])} 个文件")

    elif cmd == "check":
        changes = detect_changes(root)
        if "error" in changes:
            print(f"❌ {changes['error']}")
        else:
            print(f"📊 {changes['total_files']} 个文件，"
                  f"+{len(changes['added'])} -{len(changes['removed'])} "
                  f"~{len(changes['changed'])}")

    elif cmd == "report":
        report = generate_report(root)
        print(report)
        out = root / "changeguard_report.md"
        out.write_text(report, encoding="utf-8")
        print(f"\n📄 已保存: {out}")

    else:
        print("未知命令: " + cmd)


if __name__ == "__main__":
    main()
