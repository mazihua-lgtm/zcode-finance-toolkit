"""
ProjGen —— ZCode 项目生成器
从模板快速创建标准化项目结构，支持 ZCode Skill / Python CLI / 通用项目
"""

import os
import sys
from datetime import datetime
from pathlib import Path

TEMPLATES = {
    "zcode-skill": {
        "dirs": ["scripts"],
        "files": {
            "SKILL.md": """---
name: {name}
description: >
  {description}
---

# {title}

{description}

## 功能

- 

## 使用

```bash
python3 {{baseDir}}/scripts/{name}.py
```

## 依赖

```bash
pip install 
```
""",
            "scripts/{name}.py": """#!/usr/bin/env python3
\"\"\"
{title}
\"\"\"

def main():
    print("🚀 {title}")


if __name__ == "__main__":
    main()
""",
            "README.md": """# {title}

{description}

## 安装

```bash
git clone https://github.com/{github_user}/{name}.git
cd {name}
```

## 使用

```bash
python3 scripts/{name}.py
```

## License

MIT
""",
            ".gitignore": "__pycache__/\n*.pyc\n.DS_Store\nmiaoxiang/\n",
        },
    },
    "python-cli": {
        "dirs": [],
        "files": {
            "{name}.py": """#!/usr/bin/env python3
\"\"\"
{title}
\"\"\"

import sys


def main():
    print("🚀 {title}")


if __name__ == "__main__":
    main()
""",
            "README.md": """# {title}

{description}

## 使用

```bash
python3 {name}.py
```
""",
            ".gitignore": "__pycache__/\n*.pyc\n.DS_Store\n",
        },
    },
    "zcode-plugin": {
        "dirs": [".zcode-plugin", "skills", "hooks"],
        "files": {
            ".zcode-plugin/plugin.json": """{{
  "name": "{name}",
  "version": "1.0.0",
  "description": "{description}",
  "author": {{ "name": "{github_user}" }},
  "license": "MIT",
  "skills": "skills",
  "hooks": "hooks"
}}
""",
            "README.md": """# {title}

{description}

## 安装

```bash
git clone https://github.com/{github_user}/{name}.git ~/.zcode/skills/{name}
```

## License

MIT
""",
            ".gitignore": "__pycache__/\n*.pyc\n.DS_Store\n",
        },
    },
}


def generate(template: str, name: str, description: str = "", github_user: str = "mazihua-lgtm", output_dir: str = "") -> str:
    """生成项目骨架。"""
    tmpl = TEMPLATES.get(template)
    if not tmpl:
        return f"❌ 未知模板: {template}。可选: {', '.join(TEMPLATES.keys())}"

    title = name.replace("-", " ").title()
    desc = description or f"{title} — 一个 ZCode 项目"

    root = Path(output_dir or f"./{name}")
    if root.exists():
        return f"❌ 目录已存在: {root}"

    root.mkdir(parents=True)

    for d in tmpl["dirs"]:
        (root / d).mkdir(parents=True, exist_ok=True)

    for fpath, content in tmpl["files"].items():
        formatted = content.format(
            name=name, title=title, description=desc, github_user=github_user,
        )
        full = root / fpath.format(name=name, title=title)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_text(formatted)
        print(f"  ✅ {full.relative_to(root)}")

    return f"✅ 项目已生成: {root}"


def list_templates() -> str:
    return "📦 可用模板:\n- " + "\n- ".join(TEMPLATES.keys())


def main():
    if len(sys.argv) < 3:
        print("ProjGen —— ZCode 项目生成器")
        print()
        print("用法: projgen <模板> <项目名> [描述]")
        print()
        print(list_templates())
        print()
        print("示例:")
        print("  projgen zcode-skill my-analyzer '数据诊断工具'")
        print("  projgen python-cli hello-world")
        print("  projgen zcode-plugin my-toolkit")
        return

    template = sys.argv[1]
    name = sys.argv[2]
    desc = sys.argv[3] if len(sys.argv) > 3 else ""
    print(generate(template, name, desc))


if __name__ == "__main__":
    main()
