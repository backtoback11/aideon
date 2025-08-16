import json
from typing import Dict, Any, List

class MetaSummarizer:
    """
    Собирает сводный мета-отчёт по проекту из результата ProjectScanner.scan().
    Ожидает на вход dict вида:
      {
        "rel/dir": [
          {"name": "file.py", "summary": <str|dict>},
          ...
        ],
        ...
      }
    """

    def __init__(self) -> None:
        pass

    def build_meta_summary(self, tree: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Преобразует дерево из ProjectScanner в агрегированный мета-отчёт.
        """
        files: List[Dict[str, Any]] = []
        folders: List[Dict[str, Any]] = []
        total_lines = 0

        for rel_dir, items in sorted(tree.items()):
            folder_entry = {"path": rel_dir, "items": []}
            for it in items:
                name = it.get("name")
                summary = it.get("summary")

                # Нормализуем summary -> dict
                if isinstance(summary, str):
                    # Попробуем выделить примитивы из текстового саммари (best-effort)
                    entry = {
                        "name": name,
                        "raw_summary": summary
                    }
                elif isinstance(summary, dict):
                    entry = {
                        "name": name,
                        "lines": summary.get("lines"),
                        "classes": summary.get("classes"),
                        "functions": summary.get("functions"),
                        "todos": summary.get("todos"),
                        "tags": summary.get("tags") if "tags" in summary else None,
                        "raw_summary": None
                    }
                    if isinstance(summary.get("lines"), int):
                        total_lines += summary["lines"] or 0
                else:
                    entry = {"name": name, "raw_summary": str(summary)}

                files.append({
                    "path": f"{rel_dir}/{name}",
                    **{k: v for k, v in entry.items() if k != "name"}
                })
                folder_entry["items"].append(entry)
            folders.append(folder_entry)

        project_size_estimate = f"{total_lines} lines" if total_lines else "unknown"

        return {
            "project_size_estimate": project_size_estimate,
            "files": files,
            "folders": folders,
            "stats": {
                "folders_count": len(folders),
                "files_count": len(files)
            }
        }

    def export_json(self, meta: Dict[str, Any], path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
