#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Генерация метасаммери проекта:
- reports/meta_summary.json — полный JSON
- SUMMARY.md — краткий обзор для GitHub (или stdout по флагу)
Совместимо с расширенным MetaSummarizer (project_facts, render_markdown()).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, List

# гарантируем, что корень репозитория в sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(REPO_ROOT))

from app.modules.improver.project_scanner import ProjectScanner  # noqa: E402
from app.modules.improver.meta_summarizer import MetaSummarizer  # noqa: E402


def _safe_get(d: Dict[str, Any], path: str, default=None):
    """Безопасное извлечение по "a.b.c" из словаря."""
    cur = d
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def _render_md_fallback(meta: Dict[str, Any]) -> str:
    """Резервная сборка SUMMARY.md, если у MetaSummarizer нет render_markdown()."""
    lines: List[str] = []
    lines.append("# 📊 Project Meta Summary\n")
    lines.append("Автогенерация при каждом push.\n")

    files_count = _safe_get(meta, "stats.files_count", 0)
    lines_total = _safe_get(meta, "stats.lines_total", None)
    size_est = meta.get("project_size_estimate", "?")

    lines.append("## Краткий обзор")
    lines.append(f"- Файлов: {files_count}")
    lines.append(f"- Оценка размера проекта: ~{size_est}")
    if isinstance(lines_total, int):
        lines.append(f"- Суммарно строк кода: {lines_total}")
    lines.append("")

    # 🧭 Профиль проекта (facts)
    lines.append("## 🧭 Профиль проекта")
    py_ver = _safe_get(meta, "project_facts.python_version", "?")
    os_name = _safe_get(meta, "project_facts.os", "?")
    git_commit = _safe_get(meta, "project_facts.git.commit", "?")
    git_branch = _safe_get(meta, "project_facts.git.branch", "?")
    git_dirty = _safe_get(meta, "project_facts.git.is_dirty", False)
    model_name = _safe_get(meta, "project_facts.openai.model_name", "—")
    key_source = _safe_get(meta, "project_facts.openai.key_source", "unknown")
    features = _safe_get(meta, "project_facts.features", []) or []
    packages = _safe_get(meta, "project_facts.installed_packages", []) or []

    lines.append(f"- Python: `{py_ver}`")
    lines.append(f"- OS: `{os_name}`")
    lines.append(f"- Git: ветка `{git_branch}`, коммит `{git_commit}`, dirty: `{git_dirty}`")
    lines.append(f"- OpenAI модель: `{model_name}`")
    lines.append(f"- Источник API ключа: `{key_source}`")
    if features:
        lines.append(f"- Включённые модули: {', '.join(features)}")
    if packages:
        lines.append(f"- Установленные пакеты (top {len(packages)}):")
        for p in packages:
            lines.append(f"  - `{p}`")
    lines.append("\n---\n")

    # Детализация по папкам
    lines.append("## Детализация по папкам\n")
    folders = meta.get("folders", [])
    folders_sorted = sorted(folders, key=lambda x: (x.get("path") != ".", x.get("path", "")))
    for folder in folders_sorted:
        path = folder.get("path", "")
        lines.append(f"### {path}")
        for item in folder.get("items", []):
            name = item.get("name", "unknown")
            ln = item.get("lines")
            tags = item.get("tags")
            tags_str = ", ".join(tags) if isinstance(tags, list) and tags else "—"
            if isinstance(ln, int):
                lines.append(f"- **{name}** — {ln} строк, теги: {tags_str}")
            else:
                lines.append(f"- **{name}** — теги: {tags_str}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Generate project meta summary (JSON + Markdown).")
    p.add_argument("--json", default="reports/meta_summary.json", help="Путь для JSON (по умолчанию reports/meta_summary.json)")
    p.add_argument("--md", default="SUMMARY.md", help="Путь для Markdown (по умолчанию SUMMARY.md)")
    p.add_argument("--stdout", action="store_true", help="Вывести Markdown в stdout вместо записи в файл")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    os.chdir(REPO_ROOT)  # стабильные пути в CI

    # 1) Сканирование проекта
    scanner = ProjectScanner(root_path="app")
    tree = scanner.scan()

    # 2) Сбор метаданных
    meta = MetaSummarizer().build_meta_summary(tree)

    # 3) JSON
    json_path = Path(args.json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # 4) Markdown
    #   Если у MetaSummarizer есть render_markdown, используем её.
    md_text: str
    if hasattr(MetaSummarizer, "render_markdown"):
        try:
            md_text = MetaSummarizer().render_markdown(meta)  # type: ignore[attr-defined]
        except Exception:
            md_text = _render_md_fallback(meta)
    else:
        md_text = _render_md_fallback(meta)

    if args.stdout:
        # выводим в консоль (удобно для проверки)
        sys.stdout.write(md_text)
    else:
        md_path = Path(args.md)
        with md_path.open("w", encoding="utf-8") as f:
            f.write(md_text)

    print(f"✅ Meta summary JSON: {json_path}")
    if args.stdout:
        print("✅ SUMMARY.md: (stdout)")
    else:
        print(f"✅ SUMMARY.md: {args.md}")


if __name__ == "__main__":
    main()