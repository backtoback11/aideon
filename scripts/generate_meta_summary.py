#!/usr/bin/env python3
import json, os, sys
sys.path.append(os.path.abspath("."))

from app.modules.improver.project_scanner import ProjectScanner
from app.modules.improver.meta_summarizer import MetaSummarizer

def main():
    scanner = ProjectScanner(root_path="app")
    tree = scanner.scan()
    meta = MetaSummarizer().build_meta_summary(tree)

    os.makedirs("reports", exist_ok=True)
    with open("reports/meta_summary.json", "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    # Краткий обзор для GitHub
    with open("SUMMARY.md", "w", encoding="utf-8") as f:
        f.write("# 📊 Project Meta Summary\n\n")
        f.write("Автогенерация при каждом push.\n\n")
        f.write("## Краткий обзор\n")
        f.write(f"- Файлов: {len(meta.get('files', []))}\n")
        f.write(f"- Оценка размера проекта: ~{meta.get('project_size_estimate', '?')}\n")
        f.write("\n---\n")
        f.write("## Детализация по папкам\n\n")
        for folder in meta.get("folders", []):
            f.write(f"### {folder['path']}\n")
            for item in folder.get("items", []):
                name = item["name"]
                lines = item.get("lines")
                tags = ", ".join(item.get("tags", [])) if item.get("tags") else "—"
                f.write(f"- **{name}** — {lines} строк, теги: {tags}\n")
            f.write("\n")

if __name__ == "__main__":
    main()
