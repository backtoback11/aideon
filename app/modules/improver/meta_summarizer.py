# app/modules/improver/meta_summarizer.py
from __future__ import annotations

import json
import os
import platform
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Tuple


class MetaSummarizer:
    """
    Собирает сводный мета-отчёт по проекту из результата ProjectScanner.scan().
    На вход ожидает dict вида:
      {
        "rel/dir": [
          {
            "name": "file.py",
            "summary": <str|dict>,
            "structure": {  # опционально, если ProjectScanner это добавил
              "lines": int,
              "classes_count": int,
              "functions_count": int,
              "class_names": [..],
              "function_names": [..],
            }
          },
          ...
        ],
        ...
      }

    Выход дополняется блоком project_facts (git, python, openai, features, packages),
    а также служебными полями meta_version и generated_at.
    """

    def __init__(self, settings_path: str = "app/configs/settings.json") -> None:
        self.settings_path = Path(settings_path)

    # ---------- Публичные методы ----------

    def build_meta_summary(self, tree: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Преобразует дерево из ProjectScanner в агрегированный мета-отчёт + факты проекта.
        """
        files, folders, total_lines = self._build_summary_from_structure(tree)
        facts = self._collect_project_facts(total_lines=total_lines, files_count=len(files))

        meta: Dict[str, Any] = {
            "meta_version": "1.1",
            "generated_at": datetime.utcnow().isoformat(timespec="seconds") + "Z",
            "project_size_estimate": f"{total_lines} lines" if total_lines else "unknown",
            "files": files,
            "folders": folders,
            "stats": {
                "folders_count": len(folders),
                "files_count": len(files),
                "lines_total": total_lines,
            },
            "project_facts": facts,
        }
        return meta

    def export_json(self, meta: Dict[str, Any], path: str) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    # Опционально: готовый рендер в Markdown (если решите использовать вместо логики в scripts/)
    def render_markdown(self, meta: Dict[str, Any]) -> str:
        lines: List[str] = []
        lines.append("# 📊 Project Meta Summary\n")
        lines.append(f"_Сгенерировано_: {meta.get('generated_at', '')}\n")
        lines.append("## Краткий обзор")
        stats = meta.get("stats", {})
        lines.append(f"- Файлов: {stats.get('files_count', '?')}")
        lines.append(f"- Строк: {stats.get('lines_total', '?')}")
        lines.append(f"- Оценка размера проекта: {meta.get('project_size_estimate', '?')}\n")
        lines.append("---")
        lines.append("## Детализация по папкам\n")

        for folder in meta.get("folders", []):
            lines.append(f"### {folder.get('path', '')}")
            for item in folder.get("items", []):
                name = item.get("name", "")
                lns = item.get("lines")
                tags = ", ".join(item.get("tags", []) or []) if item.get("tags") else "—"
                classes = item.get("classes") or item.get("class_names")
                funcs = item.get("functions") or item.get("function_names")
                classes_str = ", ".join(classes) if isinstance(classes, list) else "—"
                funcs_str = ", ".join(funcs) if isinstance(funcs, list) else "—"
                lines.append(f"- **{name}** — {lns if lns is not None else '—'} строк, теги: {tags}")
                lines.append(f"  - классы: {classes_str}")
                lines.append(f"  - функции: {funcs_str}")
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    # ---------- Внутренние методы: сбор структуры ----------

    def _build_summary_from_structure(
        self,
        tree: Dict[str, List[Dict[str, Any]]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
        files: List[Dict[str, Any]] = []
        folders: List[Dict[str, Any]] = []
        total_lines = 0

        for rel_dir, items in sorted(tree.items()):
            folder_entry = {"path": rel_dir, "items": []}
            for it in items:
                name = it.get("name", "")
                summary = it.get("summary")
                structure = it.get("structure")  # может отсутствовать

                entry = self._normalize_entry(name, summary, structure)

                # Путь для files[]
                entry_with_path = {
                    "path": f"{rel_dir}/{name}" if rel_dir not in (".", "") else name,
                    **{k: v for k, v in entry.items() if k != "name"},
                }
                files.append(entry_with_path)
                folder_entry["items"].append(entry)

                # Суммируем строки (structure.lines приоритетнее summary.lines)
                lines_val = None
                if isinstance(structure, dict) and isinstance(structure.get("lines"), int):
                    lines_val = structure["lines"]
                elif isinstance(entry.get("lines"), int):
                    lines_val = entry["lines"]

                if isinstance(lines_val, int):
                    total_lines += lines_val

            folders.append(folder_entry)

        return files, folders, total_lines

    def _normalize_entry(self, name: str, summary: Any, structure: Any) -> Dict[str, Any]:
        """
        Нормализация саммари:
        - если summary — dict, берём поля (lines/classes/functions/tags/description);
        - если есть structure — аккуратно добавляем class/function names и counts;
        - если summary — строка, кладём в description.
        """
        entry: Dict[str, Any] = {"name": name}

        if isinstance(summary, dict):
            entry.update({
                "lines": summary.get("lines"),
                "classes": summary.get("classes"),
                "functions": summary.get("functions"),
                "todos": summary.get("todos"),
                "tags": summary.get("tags") if "tags" in summary else None,
                "description": self._extract_description(summary),
            })
        else:
            entry.update({
                "description": str(summary)[:2000] if summary is not None else None,
            })

        # Подмешиваем structure, если есть (не ломая старые поля)
        if isinstance(structure, dict):
            # counts
            if "classes" not in entry or not entry["classes"]:
                entry["classes"] = structure.get("class_names")
            if "functions" not in entry or not entry["functions"]:
                entry["functions"] = structure.get("function_names")
            # lines приоритетнее из structure
            if "lines" not in entry or entry["lines"] is None:
                entry["lines"] = structure.get("lines")

            # ещё оставим «сырой» блок structure, чтобы UI мог читать подробно
            entry["structure"] = {
                "lines": structure.get("lines"),
                "classes_count": structure.get("classes_count"),
                "functions_count": structure.get("functions_count"),
                "class_names": structure.get("class_names"),
                "function_names": structure.get("function_names"),
            }

        return entry

    def _extract_description(self, data: Dict[str, Any]) -> str | None:
        # Пытаемся вынуть краткое описание из dict-саммери
        for key in ("short", "description", "summary"):
            if data.get(key):
                return str(data[key])
        return None

    # ---------- Внутренние методы: сбор фактов проекта ----------

    def _collect_project_facts(self, total_lines: int, files_count: int) -> Dict[str, Any]:
        facts: Dict[str, Any] = {
            "python_version": platform.python_version(),
            "os": platform.platform(),
            "files_count": files_count,
            "lines_total": total_lines,
        }

        facts["git"] = self._git_facts()
        settings, settings_src = self._read_settings()

        facts["settings_source"] = settings_src
        facts["env"] = {
            "OPENAI_API_KEY_present": bool(os.getenv("OPENAI_API_KEY")),
        }
        facts["openai"] = {
            "model_name": self._detect_model_name(settings),
            "key_source": self._detect_key_source(settings),  # НЕ значение ключа — только источник
        }

        facts["features"] = self._features_detect()
        facts["installed_packages"] = self._pip_freeze_sample()

        return facts

    def _git_facts(self) -> Dict[str, Any]:
        def _run(cmd: List[str]) -> str | None:
            try:
                out = subprocess.check_output(
                    cmd, stderr=subprocess.DEVNULL
                ).decode("utf-8", "ignore").strip()
                return out or None
            except Exception:
                return None

        commit = _run(["git", "rev-parse", "--short", "HEAD"])
        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
        status = _run(["git", "status", "--porcelain"]) or ""
        is_dirty = bool(status.strip())
        return {"commit": commit, "branch": branch, "is_dirty": is_dirty}

    def _read_settings(self) -> Tuple[Dict[str, Any], str]:
        """
        Возвращает (settings_dict, settings_source_str)
        """
        try:
            if self.settings_path.exists():
                return json.loads(self.settings_path.read_text(encoding="utf-8")), str(self.settings_path)
        except Exception:
            pass
        return {}, "not_found"

    def _detect_model_name(self, settings: Dict[str, Any]) -> str | None:
        # Поддержка старого и нового форматов настроек
        if "model_name" in settings:
            return settings.get("model_name")
        if "openai" in settings and isinstance(settings["openai"], dict):
            return settings["openai"].get("model_name")
        return None

    def _detect_key_source(self, settings: Dict[str, Any]) -> str:
        # Только источник, НЕ само значение ключа
        if os.getenv("OPENAI_API_KEY"):
            return "env/.env|ENV"
        if any(k in settings for k in ("openai_api_key", "OPENAI_API_KEY")):
            return "settings.json(root)"
        if isinstance(settings.get("openai"), dict) and any(
            k in settings["openai"] for k in ("api_key", "OPENAI_API_KEY")
        ):
            return "settings.json(openai.api_key)"
        return "unknown"

    def _features_detect(self) -> List[str]:
        features: List[str] = []
        if Path("app/modules/ui_analyzer").exists():
            features.append("ui_analyzer")
        if Path("app/modules/self_improver.py").exists():
            features.append("self_improver")
        if Path("app/modules/improver/meta_summarizer.py").exists():
            features.append("meta_summarizer")
        if Path("app/ui/main_window.py").exists():
            features.append("qt_ui")
        return features

    def _pip_freeze_sample(self, limit: int = 10) -> List[str]:
        try:
            out = subprocess.check_output(
                [os.sys.executable, "-m", "pip", "freeze"],
                stderr=subprocess.DEVNULL
            ).decode("utf-8", "ignore").splitlines()
            out = [l for l in out if l and "@" not in l]
            out.sort()
            return out[:limit]
        except Exception:
            return []