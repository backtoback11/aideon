# 📝 Last Changes Digest

- Generated: 2025-08-17T18:18:28.334269Z
- Range: `Push diff: 1d931e8..8cde972`
- Files changed: **4**

## Changed files

```text
M	SUMMARY.md
M	app/modules/improver/meta_summarizer.py
M	reports/meta_summary.json
M	scripts/generate_meta_summary.py
```

## Diffs (unified=0)

<details><summary>SUMMARY.md</summary>

```diff
diff --git a/SUMMARY.md b/SUMMARY.md
index cc2cf77..1137a08 100644
--- a/SUMMARY.md
+++ b/SUMMARY.md
@@ -6,2 +6,22 @@
-- Файлов: 24
-- Оценка размера проекта: ~unknown
+- Файлов: 25
+- Оценка размера проекта: ~2013 lines
+- Суммарно строк кода: 2013
+
+## 🧭 Профиль проекта
+- Python: `3.12.8`
+- OS: `macOS-15.6-arm64-arm-64bit`
+- Git: ветка `main`, коммит `1d931e8`, dirty: `True`
+- OpenAI модель: `gpt-4-turbo`
+- Источник API ключа: `env/.env|ENV`
+- Включённые модули: ui_analyzer, self_improver, meta_summarizer, qt_ui
+- Установленные пакеты (top 10):
+  - `Jinja2==3.1.5`
+  - `MarkupSafe==3.0.2`
+  - `PyQt6-Qt6==6.8.2`
+  - `PyQt6==6.8.1`
+  - `PyQt6_sip==13.10.0`
+  - `PyYAML==6.0.2`
+  - `accelerate==1.3.0`
+  - `aiohappyeyeballs==2.4.6`
+  - `aiohttp==3.11.12`
+  - `aiosignal==1.3.2`
@@ -13,2 +33,2 @@
-- **utils.py** — None строк, теги: —
-- **logger.py** — None строк, теги: —
+- **logger.py** — 55 строк, теги: —
+- **utils.py** — 7 строк, теги: —
@@ -17 +37 @@
-- **file_manager.py** — None строк, теги: —
+- **file_manager.py** — 327 строк, теги: —
@@ -20,6 +40,6 @@
-- **orchestrator.py** — None строк, теги: —
-- **utils.py** — None строк, теги: —
-- **runner.py** — None строк, теги: —
-- **self_improver.py** — None строк, теги: —
-- **fixer.py** — None строк, теги: —
-- **analyzer.py** — None строк, теги: —
+- **fixer.py** — 150 строк, теги: —
+- **runner.py** — 69 строк, теги: —
+- **analyzer.py** — теги: —
+- **utils.py** — 18 строк, теги: —
+- **orchestrator.py** — 206 строк, теги: —
+- **self_improver.py** — теги: —
@@ -28,7 +48,10 @@
-- **error_debugger.py** — None строк, теги: —
-- **improvement_planner.py** — None строк, теги: —
-- **meta_summarizer.py** — None строк, теги: —
-- **patcher.py** — None строк, теги: —
-- **project_scanner.py** — None строк, теги: —
-- **file_summarizer.py** — None строк, теги: —
-- **patch_requester.py** — None строк, теги: —
+- **error_debugger.py** — 45 строк, теги: —
+- **project_scanner.py** — теги: —
+- **improvement_planner.py** — 51 строк, теги: —
+- **patcher.py** — 77 строк, теги: —
+- **patch_requester.py** — 59 строк, теги: —
+- **file_summarizer.py** — теги: —
+- **meta_summarizer.py** — теги: —
+
+### modules/ui_analyzer
+- **analyzer.py** — теги: —
@@ -37,3 +60,3 @@
-- **main_window.py** — None строк, теги: —
-- **analysis_thread.py** — None строк, теги: —
-- **chat_panel.py** — None строк, теги: —
+- **main_window.py** — теги: —
+- **chat_panel.py** — 113 строк, теги: —
+- **analysis_thread.py** — 74 строк, теги: —
@@ -42,5 +65,5 @@
-- **panel_history.py** — None строк, теги: —
-- **panel_solutions.py** — None строк, теги: —
-- **panel_issues.py** — None строк, теги: —
-- **panel_process.py** — None строк, теги: —
-- **panel_result.py** — None строк, теги: —
+- **panel_issues.py** — 27 строк, теги: —
+- **panel_solutions.py** — 126 строк, теги: —
+- **panel_history.py** — 190 строк, теги: —
+- **panel_process.py** — 364 строк, теги: —
+- **panel_result.py** — 55 строк, теги: —
```

</details>

<details><summary>app/modules/improver/meta_summarizer.py</summary>

```diff
diff --git a/app/modules/improver/meta_summarizer.py b/app/modules/improver/meta_summarizer.py
index bb75329..ac18be0 100644
--- a/app/modules/improver/meta_summarizer.py
+++ b/app/modules/improver/meta_summarizer.py
@@ -0,0 +1,2 @@
+# app/modules/improver/meta_summarizer.py
+from __future__ import annotations
@@ -2 +4,6 @@ import json
-from typing import Dict, Any, List
+import os
+import platform
+import subprocess
+from pathlib import Path
+from typing import Dict, Any, List, Tuple
+
@@ -14,0 +22,18 @@ class MetaSummarizer:
+
+    Выход дополняется блоком project_facts (git, python, openai, features, packages):
+      {
+        "project_size_estimate": "...",
+        "files": [...],
+        "folders": [...],
+        "stats": {...},
+        "project_facts": {
+            "python_version": "...",
+            "os": "...",
+            "git": {"commit": "...", "branch": "...", "is_dirty": bool},
+            "openai": {"model_name": "...", "key_source": "env/.env|settings.json|unknown"},
+            "features": ["ui_analyzer", "self_improver", ...],
+            "installed_packages": ["PyQt6==...", "openai==...", ...],
+            "files_count": N,
+            "lines_total": M
+        }
+      }
@@ -17,2 +42,4 @@ class MetaSummarizer:
-    def __init__(self) -> None:
-        pass
+    def __init__(self, settings_path: str = "app/configs/settings.json") -> None:
+        self.settings_path = Path(settings_path)
+
+    # ---------- Публичные методы ----------
@@ -22 +49 @@ class MetaSummarizer:
-        Преобразует дерево из ProjectScanner в агрегированный мета-отчёт.
+        Преобразует дерево из ProjectScanner в агрегированный мета-отчёт + факты проекта.
@@ -23,0 +51,26 @@ class MetaSummarizer:
+        files, folders, total_lines = self._build_summary_from_structure(tree)
+        facts = self._collect_project_facts(total_lines=total_lines, files_count=len(files))
+
+        return {
+            "project_size_estimate": f"{total_lines} lines" if total_lines else "unknown",
+            "files": files,
+            "folders": folders,
+            "stats": {
+                "folders_count": len(folders),
+                "files_count": len(files),
+                "lines_total": total_lines,
+            },
+            "project_facts": facts,
+        }
+
+    def export_json(self, meta: Dict[str, Any], path: str) -> None:
+        Path(path).parent.mkdir(parents=True, exist_ok=True)
+        with open(path, "w", encoding="utf-8") as f:
+            json.dump(meta, f, ensure_ascii=False, indent=2)
+
+    # ---------- Внутренние методы: сбор структуры ----------
+
+    def _build_summary_from_structure(
+        self,
+        tree: Dict[str, List[Dict[str, Any]]]
+    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
@@ -31 +84 @@ class MetaSummarizer:
-                name = it.get("name")
+                name = it.get("name", "")
@@ -34,26 +87,7 @@ class MetaSummarizer:
-                # Нормализуем summary -> dict
-                if isinstance(summary, str):
-                    # Попробуем выделить примитивы из текстового саммари (best-effort)
-                    entry = {
-                        "name": name,
-                        "raw_summary": summary
-                    }
-                elif isinstance(summary, dict):
-                    entry = {
-                        "name": name,
-                        "lines": summary.get("lines"),
-                        "classes": summary.get("classes"),
-                        "functions": summary.get("functions"),
-                        "todos": summary.get("todos"),
-                        "tags": summary.get("tags") if "tags" in summary else None,
-                        "raw_summary": None
-                    }
-                    if isinstance(summary.get("lines"), int):
-                        total_lines += summary["lines"] or 0
-                else:
-                    entry = {"name": name, "raw_summary": str(summary)}
-
-                files.append({
-                    "path": f"{rel_dir}/{name}",
-                    **{k: v for k, v in entry.items() if k != "name"}
-                })
+                entry = self._normalize_entry(name, summary)
+                # Дополняем путём
+                entry_with_path = {
+                    "path": f"{rel_dir}/{name}" if rel_dir not in (".", "") else name,
+                    **{k: v for k, v in entry.items() if k != "name"},
+                }
+                files.append(entry_with_path)
@@ -60,0 +95,5 @@ class MetaSummarizer:
+
+                # Суммируем строки
+                if isinstance(entry.get("lines"), int):
+                    total_lines += entry["lines"] or 0
+
@@ -63 +102 @@ class MetaSummarizer:
-        project_size_estimate = f"{total_lines} lines" if total_lines else "unknown"
+        return files, folders, total_lines
@@ -65,7 +104,11 @@ class MetaSummarizer:
-        return {
-            "project_size_estimate": project_size_estimate,
-            "files": files,
-            "folders": folders,
-            "stats": {
-                "folders_count": len(folders),
-                "files_count": len(files)
+    def _normalize_entry(self, name: str, summary: Any) -> Dict[str, Any]:
+        # Нормализация саммери (dict предпочтительно; строку — в raw_summary)
+        if isinstance(summary, dict):
+            return {
+                "name": name,
+                "lines": summary.get("lines"),
+                "classes": summary.get("classes"),
+                "functions": summary.get("functions"),
+                "todos": summary.get("todos"),
+                "tags": summary.get("tags") if "tags" in summary else None,
+                "description": self._extract_description(summary),
@@ -72,0 +116,3 @@ class MetaSummarizer:
+        return {
+            "name": name,
+            "description": str(summary)[:2000] if summary is not None else None,
@@ -75,3 +121,97 @@ class MetaSummarizer:
-    def export_json(self, meta: Dict[str, Any], path: str) -> None:
-        with open(path, "w", encoding="utf-8") as f:
-            json.dump(meta, f, ensure_ascii=False, indent=2)
+    def _extract_description(self, data: Dict[str, Any]) -> str | None:
+        # Пытаемся вынуть краткое описание из dict-саммери
+        for key in ("short", "description", "summary"):
+            if data.get(key):
+                return str(data[key])
+        return None
+
+    # ---------- Внутренние методы: сбор фактов проекта ----------
+
+    def _collect_project_facts(self, total_lines: int, files_count: int) -> Dict[str, Any]:
+        facts: Dict[str, Any] = {
+            "python_version": platform.python_version(),
+            "os": platform.platform(),
+            "files_count": files_count,
+            "lines_total": total_lines,
+        }
+
+        facts["git"] = self._git_facts()
+        settings = self._read_settings()
+
+        facts["openai"] = {
+            "model_name": self._detect_model_name(settings),
+            "key_source": self._detect_key_source(settings),  # НЕ значение ключа — только источник
+        }
+
+        facts["features"] = self._features_detect()
+        facts["installed_packages"] = self._pip_freeze_sample()
+
+        return facts
+
+    def _git_facts(self) -> Dict[str, Any]:
+        def _run(cmd: List[str]) -> str | None:
+            try:
+                out = subprocess.check_output(
+                    cmd, stderr=subprocess.DEVNULL
+                ).decode("utf-8", "ignore").strip()
+                return out or None
+            except Exception:
+                return None
+
+        commit = _run(["git", "rev-parse", "--short", "HEAD"])
+        branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
+        status = _run(["git", "status", "--porcelain"]) or ""
+        is_dirty = bool(status.strip())
+        return {"commit": commit, "branch": branch, "is_dirty": is_dirty}
+
+    def _read_settings(self) -> Dict[str, Any]:
+        try:
+            if self.settings_path.exists():
+                return json.loads(self.settings_path.read_text(encoding="utf-8"))
+        except Exception:
+            pass
+        return {}
+
+    def _detect_model_name(self, settings: Dict[str, Any]) -> str | None:
+        # Поддержка старого и нового форматов настроек
+        if "model_name" in settings:
+            return settings.get("model_name")
+        if "openai" in settings and isinstance(settings["openai"], dict):
+            return settings["openai"].get("model_name")
+        return None
+
+    def _detect_key_source(self, settings: Dict[str, Any]) -> str:
+        # Только источник, НЕ само значение ключа
+        if os.getenv("OPENAI_API_KEY"):
+            return "env/.env|ENV"
+        if any(k in settings for k in ("openai_api_key", "OPENAI_API_KEY")):
+            return "settings.json(root)"
+        if isinstance(settings.get("openai"), dict) and any(
+            k in settings["openai"] for k in ("api_key", "OPENAI_API_KEY")
+        ):
+            return "settings.json(openai.api_key)"
+        return "unknown"
+
+    def _features_detect(self) -> List[str]:
+        features: List[str] = []
+        if Path("app/modules/ui_analyzer").exists():
+            features.append("ui_analyzer")
+        if Path("app/modules/self_improver.py").exists():
+            features.append("self_improver")
+        if Path("app/modules/improver/meta_summarizer.py").exists():
+            features.append("meta_summarizer")
+        if Path("app/ui/main_window.py").exists():
+            features.append("qt_ui")
+        return features
+
+    def _pip_freeze_sample(self, limit: int = 10) -> List[str]:
+        try:
+            out = subprocess.check_output(
+                [os.sys.executable, "-m", "pip", "freeze"],
+                stderr=subprocess.DEVNULL
+            ).decode("utf-8", "ignore").splitlines()
+            out = [l for l in out if l and "@" not in l]
+            out.sort()
+            return out[:limit]
+        except Exception:
+            return []
\ No newline at end of file
```

</details>

<details><summary>reports/meta_summary.json</summary>

```diff
diff --git a/reports/meta_summary.json b/reports/meta_summary.json
index a09c148..574d105 100644
--- a/reports/meta_summary.json
+++ b/reports/meta_summary.json
@@ -2 +2 @@
-  "project_size_estimate": "unknown",
+  "project_size_estimate": "2013 lines",
@@ -5,2 +5,7 @@
-      "path": "./utils.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/utils.py\n# 👁️ Строк: 7\n# 🏷️ Теги: utils\n# 🧩 Классы: —\n# 🪝 Функции: load_api_key\n\n## Краткое описание:\nСодержит функции: load_api_key.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "logger.py",
+      "lines": 55,
+      "classes": 1,
+      "functions": 4,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -9,2 +14,7 @@
-      "path": "./logger.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/logger.py\n# 👁️ Строк: 55\n# 🏷️ Теги: none\n# 🧩 Классы: ColorFormatter\n# 🪝 Функции: log_info, log_warning, log_error, format\n\n## Краткое описание:\nМодуль для логирования событий, ошибок и информации в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "utils.py",
+      "lines": 7,
+      "classes": 0,
+      "functions": 1,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -14 +24,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/core/file_manager.py\n# 👁️ Строк: 327\n# 🏷️ Теги: core\n# 🧩 Классы: FileManager\n# 🪝 Функции: __init__, open_file_dialog, open_project_dialog, save_file, read_file, list_files, delete_file, _save_to_history, _load_history, _remove_from_history, _save_project_tree, get_project_tree, _ignore_filter, _should_skip_dir, _should_skip_file, _too_long_path\n\n## Краткое описание:\nМодуль для управления файлами и их содержимым в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 327,
+      "classes": 1,
+      "functions": 16,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -17,2 +32,7 @@
-      "path": "modules/orchestrator.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/orchestrator.py\n# 👁️ Строк: 206\n# 🏷️ Теги: none\n# 🧩 Классы: Orchestrator\n# 🪝 Функции: __init__, _load_db, _save_db, add_project, set_file_summary, get_file_summary, ask_chatgpt, create_file_summary, analyze_project_chunks, run_big_scenario, _create_project_summary, _ask_gpt_for_plan, _save_orch_data\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/fixer.py",
+      "lines": 150,
+      "classes": 1,
+      "functions": 7,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -21,2 +41,7 @@
-      "path": "modules/utils.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/utils.py\n# 👁️ Строк: 18\n# 🏷️ Теги: utils\n# 🧩 Классы: —\n# 🪝 Функции: load_api_key\n\n## Краткое описание:\nСодержит функции: load_api_key.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/runner.py",
+      "lines": 69,
+      "classes": 1,
+      "functions": 3,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -25,2 +50,2 @@
-      "path": "modules/runner.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/runner.py\n# 👁️ Строк: 69\n# 🏷️ Теги: none\n# 🧩 Классы: CodeRunner\n# 🪝 Функции: __init__, run_code, run_all_tests\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/analyzer.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/analyzer.py\n# 👁️ Строк: 168\n# 🏷️ Теги: none\n# 🧩 Классы: CodeAnalyzer\n# 🪝 Функции: __init__, chat, analyze_code, _analyze_single_chunk, generate_code_star_coder, _split_into_chunks, _chat_call\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -29,2 +54,7 @@
-      "path": "modules/self_improver.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/self_improver.py\n# 👁️ Строк: 221\n# 🏷️ Теги: none\n# 🧩 Классы: SelfImprover\n# 🪝 Функции: __init__, run_self_improvement, suggest_new_features, solve_with_gpt, add_module_by_task\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/utils.py",
+      "lines": 18,
+      "classes": 0,
+      "functions": 1,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -33,2 +63,7 @@
-      "path": "modules/fixer.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/fixer.py\n# 👁️ Строк: 150\n# 🏷️ Теги: none\n# 🧩 Классы: CodeFixer\n# 🪝 Функции: __init__, suggest_fixes, apply_fixes, generate_diff, run_tests, _save_to_history, _load_history\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/orchestrator.py",
+      "lines": 206,
+      "classes": 1,
+      "functions": 13,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -37,2 +72,2 @@
-      "path": "modules/analyzer.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/analyzer.py\n# 👁️ Строк: 129\n# 🏷️ Теги: none\n# 🧩 Классы: CodeAnalyzer\n# 🪝 Функции: __init__, chat, analyze_code, _analyze_single_chunk, generate_code_star_coder, _split_into_chunks\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/self_improver.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/self_improver.py\n# 👁️ Строк: 197\n# 🏷️ Теги: none\n# 🧩 Классы: SelfImprover\n# 🪝 Функции: __init__, run_self_improvement\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -42 +77,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/error_debugger.py\n# 👁️ Строк: 45\n# 🏷️ Теги: none\n# 🧩 Классы: ErrorDebugger\n# 🪝 Функции: __init__, build_prompt, request_fix\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 45,
+      "classes": 1,
+      "functions": 3,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -45,2 +85,2 @@
-      "path": "modules/improver/improvement_planner.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/improvement_planner.py\n# 👁️ Строк: 51\n# 🏷️ Теги: none\n# 🧩 Классы: ImprovementPlanner\n# 🪝 Функции: get_improvement_plan, build_prompt, extract_plan\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/improver/project_scanner.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/project_scanner.py\n# 👁️ Строк: 142\n# 🏷️ Теги: none\n# 🧩 Классы: ProjectScanner\n# 🪝 Функции: is_hidden, is_copy_or_temp, __init__, scan, _should_ignore, _is_valid_file, _hash_file, _load_cache, _save_cache\n\n## Краткое описание:\nСканирует структуру проекта, формирует дерево файлов и summary.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -49,2 +89,7 @@
-      "path": "modules/improver/meta_summarizer.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/meta_summarizer.py\n# 👁️ Строк: 77\n# 🏷️ Теги: none\n# 🧩 Классы: MetaSummarizer\n# 🪝 Функции: __init__, build_meta_summary, export_json\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/improver/improvement_planner.py",
+      "lines": 51,
+      "classes": 1,
+      "functions": 3,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -54 +99,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/patcher.py\n# 👁️ Строк: 77\n# 🏷️ Теги: none\n# 🧩 Классы: CodePatcher\n# 🪝 Функции: __init__, confirm_and_apply_patch, _backup, _write_code, _generate_diff, _save_diff\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 77,
+      "classes": 1,
+      "functions": 6,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -57,2 +107,7 @@
-      "path": "modules/improver/project_scanner.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/project_scanner.py\n# 👁️ Строк: 142\n# 🏷️ Теги: none\n# 🧩 Классы: ProjectScanner\n# 🪝 Функции: is_hidden, is_copy_or_temp, __init__, scan, _should_ignore, _is_valid_file, _hash_file, _load_cache, _save_cache\n\n## Краткое описание:\nСканирует структуру проекта, формирует дерево файлов и summary.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/improver/patch_requester.py",
+      "lines": 59,
+      "classes": 1,
+      "functions": 2,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -62 +117 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/file_summarizer.py\n# 👁️ Строк: 96\n# 🏷️ Теги: none\n# 🧩 Классы: FileSummarizer\n# 🪝 Функции: summarize_code, summarize, _parse_structure, _infer_tags, _guess_purpose\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/file_summarizer.py\n# 👁️ Строк: 96\n# 🏷️ Теги: none\n# 🧩 Классы: FileSummarizer\n# 🪝 Функции: summarize_code, summarize, _parse_structure, _infer_tags, _guess_purpose\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -65,2 +120,2 @@
-      "path": "modules/improver/patch_requester.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/patch_requester.py\n# 👁️ Строк: 59\n# 🏷️ Теги: none\n# 🧩 Классы: PatchRequester\n# 🪝 Функции: request_code_patch, build_prompt\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/improver/meta_summarizer.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/meta_summarizer.py\n# 👁️ Строк: 217\n# 🏷️ Теги: none\n# 🧩 Классы: MetaSummarizer\n# 🪝 Функции: __init__, build_meta_summary, export_json, _build_summary_from_structure, _normalize_entry, _extract_description, _collect_project_facts, _git_facts, _read_settings, _detect_model_name, _detect_key_source, _features_detect, _pip_freeze_sample, _run\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -69,2 +124,2 @@
-      "path": "ui/main_window.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/main_window.py\n# 👁️ Строк: 323\n# 🏷️ Теги: core\n# 🧩 Классы: SelfImproverPanel, MainWindow\n# 🪝 Функции: __init__, _init_ui, start_manual_improvement, do_next_step, stop_process, reset_buttons, show_meta_summary, add_ai_idea, generate_ai_idea, update_ai_ideas_tab, add_task, generate_ai_task, update_tasks_tab, update_history_tab, __init__, _create_menu_bar, _init_ui, load_settings, save_settings, closeEvent\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "modules/ui_analyzer/analyzer.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/ui_analyzer/analyzer.py\n# 👁️ Строк: 32\n# 🏷️ Теги: none\n# 🧩 Классы: UIEvent, UIAnalyzer\n# 🪝 Функции: __init__, track, snapshot, recommend\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -73,2 +128,2 @@
-      "path": "ui/analysis_thread.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/analysis_thread.py\n# 👁️ Строк: 74\n# 🏷️ Теги: none\n# 🧩 Классы: LoadAIThread\n# 🪝 Функции: __init__, run, stop, on_progress\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "ui/main_window.py",
+      "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/ui/main_window.py\n# 👁️ Строк: 328\n# 🏷️ Теги: core\n# 🧩 Классы: SelfImproverPanel, MainWindow\n# 🪝 Функции: __init__, _init_ui, start_manual_improvement, do_next_step, stop_process, reset_buttons, show_meta_summary, add_ai_idea, generate_ai_idea, update_ai_ideas_tab, add_task, generate_ai_task, update_tasks_tab, update_history_tab, __init__, _create_menu_bar, _init_ui, load_settings, save_settings, closeEvent\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -78 +133,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/chat_panel.py\n# 👁️ Строк: 113\n# 🏷️ Теги: none\n# 🧩 Классы: ChatPanel\n# 🪝 Функции: __init__, _init_ui, handle_send_chat_gpt, add_gpt_request, add_gpt_response, add_user_message, _log_chat\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 113,
+      "classes": 1,
+      "functions": 7,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -81,2 +141,16 @@
-      "path": "ui/panels/panel_history.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_history.py\n# 👁️ Строк: 190\n# 🏷️ Теги: none\n# 🧩 Классы: PanelHistory\n# 🪝 Функции: __init__, _init_ui, load_history, show_details, compare_fixes, clear_history, _load_history\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "ui/analysis_thread.py",
+      "lines": 74,
+      "classes": 1,
+      "functions": 4,
+      "todos": 0,
+      "tags": null,
+      "description": null
+    },
+    {
+      "path": "ui/panels/panel_issues.py",
+      "lines": 27,
+      "classes": 1,
+      "functions": 3,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -86 +160,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_solutions.py\n# 👁️ Строк: 126\n# 🏷️ Теги: none\n# 🧩 Классы: PanelSolutions\n# 🪝 Функции: __init__, _init_ui, setText, show_diff, apply_fixes, rollback_changes\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 126,
+      "classes": 1,
+      "functions": 6,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -89,2 +168,7 @@
-      "path": "ui/panels/panel_issues.py",
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_issues.py\n# 👁️ Строк: 27\n# 🏷️ Теги: none\n# 🧩 Классы: PanelIssues\n# 🪝 Функции: __init__, _init_ui, setText\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "path": "ui/panels/panel_history.py",
+      "lines": 190,
+      "classes": 1,
+      "functions": 7,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -94 +178,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_process.py\n# 👁️ Строк: 364\n# 🏷️ Теги: none\n# 🧩 Классы: TestThread, PanelProcess\n# 🪝 Функции: __init__, run, stop, __init__, _init_ui, setText, run_test, stop_test, append_log_line, on_test_finished, on_test_error, rollback_changes, clear_logs, _save_test_history, _save_rollback_history, _append_history, _load_history, _append_log, _update_resource_stats\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 364,
+      "classes": 2,
+      "functions": 19,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -98 +187,6 @@
-      "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_result.py\n# 👁️ Строк: 55\n# 🏷️ Теги: none\n# 🧩 Классы: PanelResult\n# 🪝 Функции: __init__, _init_ui, setText, save_code\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+      "lines": 55,
+      "classes": 1,
+      "functions": 4,
+      "todos": 0,
+      "tags": null,
+      "description": null
@@ -106,2 +200,7 @@
-          "name": "utils.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/utils.py\n# 👁️ Строк: 7\n# 🏷️ Теги: utils\n# 🧩 Классы: —\n# 🪝 Функции: load_api_key\n\n## Краткое описание:\nСодержит функции: load_api_key.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "logger.py",
+          "lines": 55,
+          "classes": 1,
+          "functions": 4,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -110,2 +209,7 @@
-          "name": "logger.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/logger.py\n# 👁️ Строк: 55\n# 🏷️ Теги: none\n# 🧩 Классы: ColorFormatter\n# 🪝 Функции: log_info, log_warning, log_error, format\n\n## Краткое описание:\nМодуль для логирования событий, ошибок и информации в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "utils.py",
+          "lines": 7,
+          "classes": 0,
+          "functions": 1,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -120 +224,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/core/file_manager.py\n# 👁️ Строк: 327\n# 🏷️ Теги: core\n# 🧩 Классы: FileManager\n# 🪝 Функции: __init__, open_file_dialog, open_project_dialog, save_file, read_file, list_files, delete_file, _save_to_history, _load_history, _remove_from_history, _save_project_tree, get_project_tree, _ignore_filter, _should_skip_dir, _should_skip_file, _too_long_path\n\n## Краткое описание:\nМодуль для управления файлами и их содержимым в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 327,
+          "classes": 1,
+          "functions": 16,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -128,2 +237,7 @@
-          "name": "orchestrator.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/orchestrator.py\n# 👁️ Строк: 206\n# 🏷️ Теги: none\n# 🧩 Классы: Orchestrator\n# 🪝 Функции: __init__, _load_db, _save_db, add_project, set_file_summary, get_file_summary, ask_chatgpt, create_file_summary, analyze_project_chunks, run_big_scenario, _create_project_summary, _ask_gpt_for_plan, _save_orch_data\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "fixer.py",
+          "lines": 150,
+          "classes": 1,
+          "functions": 7,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -132,2 +246,7 @@
-          "name": "utils.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/utils.py\n# 👁️ Строк: 18\n# 🏷️ Теги: utils\n# 🧩 Классы: —\n# 🪝 Функции: load_api_key\n\n## Краткое описание:\nСодержит функции: load_api_key.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "runner.py",
+          "lines": 69,
+          "classes": 1,
+          "functions": 3,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -136,2 +255,2 @@
-          "name": "runner.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/runner.py\n# 👁️ Строк: 69\n# 🏷️ Теги: none\n# 🧩 Классы: CodeRunner\n# 🪝 Функции: __init__, run_code, run_all_tests\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "analyzer.py",
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/analyzer.py\n# 👁️ Строк: 168\n# 🏷️ Теги: none\n# 🧩 Классы: CodeAnalyzer\n# 🪝 Функции: __init__, chat, analyze_code, _analyze_single_chunk, generate_code_star_coder, _split_into_chunks, _chat_call\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -140,2 +259,7 @@
-          "name": "self_improver.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/self_improver.py\n# 👁️ Строк: 221\n# 🏷️ Теги: none\n# 🧩 Классы: SelfImprover\n# 🪝 Функции: __init__, run_self_improvement, suggest_new_features, solve_with_gpt, add_module_by_task\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "utils.py",
+          "lines": 18,
+          "classes": 0,
+          "functions": 1,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -144,2 +268,7 @@
-          "name": "fixer.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/fixer.py\n# 👁️ Строк: 150\n# 🏷️ Теги: none\n# 🧩 Классы: CodeFixer\n# 🪝 Функции: __init__, suggest_fixes, apply_fixes, generate_diff, run_tests, _save_to_history, _load_history\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "orchestrator.py",
+          "lines": 206,
+          "classes": 1,
+          "functions": 13,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -148,2 +277,2 @@
-          "name": "analyzer.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/analyzer.py\n# 👁️ Строк: 129\n# 🏷️ Теги: none\n# 🧩 Классы: CodeAnalyzer\n# 🪝 Функции: __init__, chat, analyze_code, _analyze_single_chunk, generate_code_star_coder, _split_into_chunks\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "self_improver.py",
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/self_improver.py\n# 👁️ Строк: 197\n# 🏷️ Теги: none\n# 🧩 Классы: SelfImprover\n# 🪝 Функции: __init__, run_self_improvement\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -158 +287,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/error_debugger.py\n# 👁️ Строк: 45\n# 🏷️ Теги: none\n# 🧩 Классы: ErrorDebugger\n# 🪝 Функции: __init__, build_prompt, request_fix\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 45,
+          "classes": 1,
+          "functions": 3,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -161,2 +295,2 @@
-          "name": "improvement_planner.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/improvement_planner.py\n# 👁️ Строк: 51\n# 🏷️ Теги: none\n# 🧩 Классы: ImprovementPlanner\n# 🪝 Функции: get_improvement_plan, build_prompt, extract_plan\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "project_scanner.py",
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/project_scanner.py\n# 👁️ Строк: 142\n# 🏷️ Теги: none\n# 🧩 Классы: ProjectScanner\n# 🪝 Функции: is_hidden, is_copy_or_temp, __init__, scan, _should_ignore, _is_valid_file, _hash_file, _load_cache, _save_cache\n\n## Краткое описание:\nСканирует структуру проекта, формирует дерево файлов и summary.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -165,2 +299,7 @@
-          "name": "meta_summarizer.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/meta_summarizer.py\n# 👁️ Строк: 77\n# 🏷️ Теги: none\n# 🧩 Классы: MetaSummarizer\n# 🪝 Функции: __init__, build_meta_summary, export_json\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "improvement_planner.py",
+          "lines": 51,
+          "classes": 1,
+          "functions": 3,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -170 +309,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/patcher.py\n# 👁️ Строк: 77\n# 🏷️ Теги: none\n# 🧩 Классы: CodePatcher\n# 🪝 Функции: __init__, confirm_and_apply_patch, _backup, _write_code, _generate_diff, _save_diff\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 77,
+          "classes": 1,
+          "functions": 6,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -173,2 +317,7 @@
-          "name": "project_scanner.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/project_scanner.py\n# 👁️ Строк: 142\n# 🏷️ Теги: none\n# 🧩 Классы: ProjectScanner\n# 🪝 Функции: is_hidden, is_copy_or_temp, __init__, scan, _should_ignore, _is_valid_file, _hash_file, _load_cache, _save_cache\n\n## Краткое описание:\nСканирует структуру проекта, формирует дерево файлов и summary.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "patch_requester.py",
+          "lines": 59,
+          "classes": 1,
+          "functions": 2,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -178 +327 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/file_summarizer.py\n# 👁️ Строк: 96\n# 🏷️ Теги: none\n# 🧩 Классы: FileSummarizer\n# 🪝 Функции: summarize_code, summarize, _parse_structure, _infer_tags, _guess_purpose\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/file_summarizer.py\n# 👁️ Строк: 96\n# 🏷️ Теги: none\n# 🧩 Классы: FileSummarizer\n# 🪝 Функции: summarize_code, summarize, _parse_structure, _infer_tags, _guess_purpose\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -181,2 +330,11 @@
-          "name": "patch_requester.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/modules/improver/patch_requester.py\n# 👁️ Строк: 59\n# 🏷️ Теги: none\n# 🧩 Классы: PatchRequester\n# 🪝 Функции: request_code_patch, build_prompt\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "meta_summarizer.py",
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/improver/meta_summarizer.py\n# 👁️ Строк: 217\n# 🏷️ Теги: none\n# 🧩 Классы: MetaSummarizer\n# 🪝 Функции: __init__, build_meta_summary, export_json, _build_summary_from_structure, _normalize_entry, _extract_description, _collect_project_facts, _git_facts, _read_settings, _detect_model_name, _detect_key_source, _features_detect, _pip_freeze_sample, _run\n\n## Краткое описание:\nМодуль для самоусовершенствования и автогенерации изменений в проекте.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+        }
+      ]
+    },
+    {
+      "path": "modules/ui_analyzer",
+      "items": [
+        {
+          "name": "analyzer.py",
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/modules/ui_analyzer/analyzer.py\n# 👁️ Строк: 32\n# 🏷️ Теги: none\n# 🧩 Классы: UIEvent, UIAnalyzer\n# 🪝 Функции: __init__, track, snapshot, recommend\n\n## Краткое описание:\nМодуль для анализа кода и генерации промтов для AI.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -191 +349 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/main_window.py\n# 👁️ Строк: 323\n# 🏷️ Теги: core\n# 🧩 Классы: SelfImproverPanel, MainWindow\n# 🪝 Функции: __init__, _init_ui, start_manual_improvement, do_next_step, stop_process, reset_buttons, show_meta_summary, add_ai_idea, generate_ai_idea, update_ai_ideas_tab, add_task, generate_ai_task, update_tasks_tab, update_history_tab, __init__, _create_menu_bar, _init_ui, load_settings, save_settings, closeEvent\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "description": "# 📁 Путь: /Users/backtoback/aideon_5.0/app/ui/main_window.py\n# 👁️ Строк: 328\n# 🏷️ Теги: core\n# 🧩 Классы: SelfImproverPanel, MainWindow\n# 🪝 Функции: __init__, _init_ui, start_manual_improvement, do_next_step, stop_process, reset_buttons, show_meta_summary, add_ai_idea, generate_ai_idea, update_ai_ideas_tab, add_task, generate_ai_task, update_tasks_tab, update_history_tab, __init__, _create_menu_bar, _init_ui, load_settings, save_settings, closeEvent\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
@@ -194,2 +352,7 @@
-          "name": "analysis_thread.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/analysis_thread.py\n# 👁️ Строк: 74\n# 🏷️ Теги: none\n# 🧩 Классы: LoadAIThread\n# 🪝 Функции: __init__, run, stop, on_progress\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "chat_panel.py",
+          "lines": 113,
+          "classes": 1,
+          "functions": 7,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -198,2 +361,7 @@
-          "name": "chat_panel.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/chat_panel.py\n# 👁️ Строк: 113\n# 🏷️ Теги: none\n# 🧩 Классы: ChatPanel\n# 🪝 Функции: __init__, _init_ui, handle_send_chat_gpt, add_gpt_request, add_gpt_response, add_user_message, _log_chat\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "analysis_thread.py",
+          "lines": 74,
+          "classes": 1,
+          "functions": 4,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -207,2 +375,7 @@
-          "name": "panel_history.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_history.py\n# 👁️ Строк: 190\n# 🏷️ Теги: none\n# 🧩 Классы: PanelHistory\n# 🪝 Функции: __init__, _init_ui, load_history, show_details, compare_fixes, clear_history, _load_history\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "panel_issues.py",
+          "lines": 27,
+          "classes": 1,
+          "functions": 3,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -212 +385,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_solutions.py\n# 👁️ Строк: 126\n# 🏷️ Теги: none\n# 🧩 Классы: PanelSolutions\n# 🪝 Функции: __init__, _init_ui, setText, show_diff, apply_fixes, rollback_changes\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 126,
+          "classes": 1,
+          "functions": 6,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -215,2 +393,7 @@
-          "name": "panel_issues.py",
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_issues.py\n# 👁️ Строк: 27\n# 🏷️ Теги: none\n# 🧩 Классы: PanelIssues\n# 🪝 Функции: __init__, _init_ui, setText\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "name": "panel_history.py",
+          "lines": 190,
+          "classes": 1,
+          "functions": 7,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -220 +403,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_process.py\n# 👁️ Строк: 364\n# 🏷️ Теги: none\n# 🧩 Классы: TestThread, PanelProcess\n# 🪝 Функции: __init__, run, stop, __init__, _init_ui, setText, run_test, stop_test, append_log_line, on_test_finished, on_test_error, rollback_changes, clear_logs, _save_test_history, _save_rollback_history, _append_history, _load_history, _append_log, _update_resource_stats\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 364,
+          "classes": 2,
+          "functions": 19,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -224 +412,6 @@
-          "raw_summary": "# 📁 Путь: /home/runner/work/aideon/aideon/app/ui/panels/panel_result.py\n# 👁️ Строк: 55\n# 🏷️ Теги: none\n# 🧩 Классы: PanelResult\n# 🪝 Функции: __init__, _init_ui, setText, save_code\n\n## Краткое описание:\nPython-модуль проекта Aideon. Требует ручного описания для точности.\n\n🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
+          "lines": 55,
+          "classes": 1,
+          "functions": 4,
+          "todos": 0,
+          "tags": null,
+          "description": null
@@ -230,2 +423,36 @@
-    "folders_count": 6,
-    "files_count": 24
+    "folders_count": 7,
+    "files_count": 25,
+    "lines_total": 2013
+  },
+  "project_facts": {
+    "python_version": "3.12.8",
+    "os": "macOS-15.6-arm64-arm-64bit",
+    "files_count": 25,
+    "lines_total": 2013,
+    "git": {
+      "commit": "1d931e8",
+      "branch": "main",
+      "is_dirty": true
+    },
+    "openai": {
+      "model_name": "gpt-4-turbo",
+      "key_source": "env/.env|ENV"
+    },
+    "features": [
+      "ui_analyzer",
+      "self_improver",
+      "meta_summarizer",
+      "qt_ui"
+    ],
+    "installed_packages": [
+      "Jinja2==3.1.5",
+      "MarkupSafe==3.0.2",
+      "PyQt6-Qt6==6.8.2",
+      "PyQt6==6.8.1",
+      "PyQt6_sip==13.10.0",
+      "PyYAML==6.0.2",
+      "accelerate==1.3.0",
+      "aiohappyeyeballs==2.4.6",
+      "aiohttp==3.11.12",
+      "aiosignal==1.3.2"
+    ]
```

</details>

<details><summary>scripts/generate_meta_summary.py</summary>

```diff
diff --git a/scripts/generate_meta_summary.py b/scripts/generate_meta_summary.py
index f19ee60..b6fc7ba 100755
--- a/scripts/generate_meta_summary.py
+++ b/scripts/generate_meta_summary.py
@@ -2,2 +2,8 @@
-import json, os, sys
-sys.path.append(os.path.abspath("."))
+# -*- coding: utf-8 -*-
+"""
+Генерация метасаммери проекта:
+- reports/meta_summary.json — полный JSON
+- SUMMARY.md — краткий обзор для GitHub
+Совместимо с расширенным MetaSummarizer (project_facts).
+"""
+from __future__ import annotations
@@ -5,2 +11,5 @@ sys.path.append(os.path.abspath("."))
-from app.modules.improver.project_scanner import ProjectScanner
-from app.modules.improver.meta_summarizer import MetaSummarizer
+import json
+import os
+import sys
+from pathlib import Path
+from typing import Dict, Any
@@ -8 +17,24 @@ from app.modules.improver.meta_summarizer import MetaSummarizer
-def main():
+# гарантируем, что корень репозитория в sys.path
+REPO_ROOT = Path(__file__).resolve().parent.parent
+sys.path.append(str(REPO_ROOT))
+
+from app.modules.improver.project_scanner import ProjectScanner  # noqa: E402
+from app.modules.improver.meta_summarizer import MetaSummarizer  # noqa: E402
+
+
+def _safe_get(d: Dict[str, Any], path: str, default=None):
+    """
+    Безопасное извлечение по "a.b.c" из словаря.
+    """
+    cur = d
+    for part in path.split("."):
+        if not isinstance(cur, dict) or part not in cur:
+            return default
+        cur = cur[part]
+    return cur
+
+
+def main() -> None:
+    os.chdir(REPO_ROOT)  # чтобы пути были стабильными при запуске из CI
+
+    # 1) Сканирование проекта
@@ -10,0 +43,2 @@ def main():
+
+    # 2) Сбор метаданных
@@ -13,2 +47,5 @@ def main():
-    os.makedirs("reports", exist_ok=True)
-    with open("reports/meta_summary.json", "w", encoding="utf-8") as f:
+    # 3) Вывод JSON
+    reports_dir = Path("reports")
+    reports_dir.mkdir(parents=True, exist_ok=True)
+    meta_json_path = reports_dir / "meta_summary.json"
+    with meta_json_path.open("w", encoding="utf-8") as f:
@@ -17,2 +54,3 @@ def main():
-    # Краткий обзор для GitHub
-    with open("SUMMARY.md", "w", encoding="utf-8") as f:
+    # 4) Краткий обзор (Markdown)
+    summary_md = Path("SUMMARY.md")
+    with summary_md.open("w", encoding="utf-8") as f:
@@ -20,0 +59,4 @@ def main():
+
+        files_count = _safe_get(meta, "stats.files_count", 0)
+        lines_total = _safe_get(meta, "stats.lines_total", None)
+        size_est = meta.get("project_size_estimate", "?")
@@ -22,2 +64,29 @@ def main():
-        f.write(f"- Файлов: {len(meta.get('files', []))}\n")
-        f.write(f"- Оценка размера проекта: ~{meta.get('project_size_estimate', '?')}\n")
+        f.write(f"- Файлов: {files_count}\n")
+        f.write(f"- Оценка размера проекта: ~{size_est}\n")
+        if isinstance(lines_total, int):
+            f.write(f"- Суммарно строк кода: {lines_total}\n")
+        f.write("\n")
+
+        # 🧭 Профиль проекта (facts)
+        f.write("## 🧭 Профиль проекта\n")
+        py_ver = _safe_get(meta, "project_facts.python_version", "?")
+        os_name = _safe_get(meta, "project_facts.os", "?")
+        git_commit = _safe_get(meta, "project_facts.git.commit", "?")
+        git_branch = _safe_get(meta, "project_facts.git.branch", "?")
+        git_dirty = _safe_get(meta, "project_facts.git.is_dirty", False)
+        model_name = _safe_get(meta, "project_facts.openai.model_name", "—")
+        key_source = _safe_get(meta, "project_facts.openai.key_source", "unknown")
+        features = _safe_get(meta, "project_facts.features", []) or []
+        packages = _safe_get(meta, "project_facts.installed_packages", []) or []
+
+        f.write(f"- Python: `{py_ver}`\n")
+        f.write(f"- OS: `{os_name}`\n")
+        f.write(f"- Git: ветка `{git_branch}`, коммит `{git_commit}`, dirty: `{git_dirty}`\n")
+        f.write(f"- OpenAI модель: `{model_name}`\n")
+        f.write(f"- Источник API ключа: `{key_source}`\n")
+        if features:
+            f.write(f"- Включённые модули: {', '.join(features)}\n")
+        if packages:
+            f.write(f"- Установленные пакеты (top {len(packages)}):\n")
+            for p in packages:
+                f.write(f"  - `{p}`\n")
@@ -24,0 +94,2 @@ def main():
+
+        # Детализация по папкам
@@ -26,2 +97,6 @@ def main():
-        for folder in meta.get("folders", []):
-            f.write(f"### {folder['path']}\n")
+        folders = meta.get("folders", [])
+        # сортируем, чтобы . шёл первым
+        folders_sorted = sorted(folders, key=lambda x: (x.get("path") != ".", x.get("path", "")))
+        for folder in folders_sorted:
+            path = folder.get("path", "")
+            f.write(f"### {path}\n")
@@ -29 +104 @@ def main():
-                name = item["name"]
+                name = item.get("name", "unknown")
@@ -31,2 +106,6 @@ def main():
-                tags = ", ".join(item.get("tags", [])) if item.get("tags") else "—"
-                f.write(f"- **{name}** — {lines} строк, теги: {tags}\n")
+                tags = item.get("tags")
+                tags_str = ", ".join(tags) if isinstance(tags, list) and tags else "—"
+                if isinstance(lines, int):
+                    f.write(f"- **{name}** — {lines} строк, теги: {tags_str}\n")
+                else:
+                    f.write(f"- **{name}** — теги: {tags_str}\n")
@@ -34,0 +114,4 @@ def main():
+    print(f"✅ Meta summary JSON: {meta_json_path}")
+    print(f"✅ SUMMARY.md: {summary_md}")
+
+
@@ -36 +119 @@ if __name__ == "__main__":
-    main()
+    main()
\ No newline at end of file
```

</details>