# app/modules/improver/project_scanner.py
from __future__ import annotations

import os
import ast
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List

from app.logger import log_info, log_warning, log_error
from app.modules.improver.file_summarizer import FileSummarizer

SCAN_CACHE_PATH = "app/data/scan_cache.json"
ALLOWED_EXTENSIONS = {".py"}

IGNORE_FOLDERS = {
    "sandbox", "venv", ".venv", "env", "__pycache__", ".git",
    "site-packages", "frontend_old", "tests", "testdata"
}
IGNORE_PATTERNS = ["копия", "copy", "backup", "tmp", "bak", "~"]


def is_hidden(filename: str) -> bool:
    return filename.startswith(".") or filename.startswith("_")


def is_copy_or_temp(filename: str) -> bool:
    low = filename.lower()
    return any(pat in low for pat in IGNORE_PATTERNS)


class ProjectScanner:
    """
    🔍 Сканирует проект, исключая sandbox/venv/копии.
    Формирует дерево файлов и кэширует результаты.

    Теперь для каждого файла:
      - summary: dict {
          lines, classes, functions, todos, tags, status, raw_summary
        }
      - structure: dict {lines, classes_count, functions_count, class_names, function_names}
        (для обратной совместимости с прежними потребителями)
    """

    def __init__(self, root_path: str = "app"):
        self.root_path = os.path.abspath(root_path)
        self.cache: Dict[str, Any] = self._load_cache()
        self.updated_cache: Dict[str, Any] = {}
        self.summarizer = FileSummarizer()

    def scan(self) -> Dict[str, List[Dict[str, Any]]]:
        log_info(f"[ProjectScanner] 🔍 Начало сканирования директории: {self.root_path}")
        tree: Dict[str, List[Dict[str, Any]]] = {}

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # фильтруем поддиректории на месте
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore(os.path.join(dirpath, d))
                and not is_hidden(d)
                and not is_copy_or_temp(d)
            ]

            rel_dir = os.path.relpath(dirpath, self.root_path)
            valid_files: List[Dict[str, Any]] = []

            for fname in filenames:
                if not self._is_valid_file(fname, dirpath):
                    continue

                full_path = os.path.join(dirpath, fname)
                file_hash = self._hash_file(full_path)

                # --- Попытка взять из кэша ---
                cached = self.cache.get(full_path)
                if cached and cached.get("hash") == file_hash:
                    summary = cached.get("summary")
                    structure = cached.get("structure")  # legacy совместимость
                    # мигрируем старый формат (строка) в dict
                    if isinstance(summary, str):
                        summary = {
                            "lines": None,
                            "classes": None,
                            "functions": None,
                            "todos": 0,
                            "tags": None,
                            "status": "legacy",
                            "raw_summary": summary,
                        }
                    log_info(f"[ProjectScanner] ⚡ Кэш использован для: {fname}")
                else:
                    # --- Читаем файл и строим summary ---
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception as e:
                        log_warning(f"[ProjectScanner] ⚠️ Ошибка при чтении {fname}: {e}")
                        continue

                    # 1) Человеческое краткое описание
                    try:
                        raw_text = self.summarizer.summarize(full_path, content)
                    except Exception as e:
                        raw_text = f"(summarizer error: {e})"

                    # 2) Структура (AST → fallback regex), + теги/статус/todo
                    structure_full = self._structure_full(full_path, content)

                    # 3) summary dict (богатая версия)
                    summary = {
                        **structure_full,
                        "raw_summary": raw_text,
                    }

                    # 4) legacy structure (counts + имена)
                    structure = self._structure_legacy(structure_full)

                    log_info(f"[ProjectScanner] 📄 Новый метасаммери: {fname}")

                # --- Обновляем кэш и дерево ---
                self.updated_cache[full_path] = {
                    "hash": file_hash,
                    "summary": summary,
                    "structure": structure,  # оставляем для совместимости
                    "timestamp": datetime.now().isoformat(),
                }

                file_entry: Dict[str, Any] = {"name": fname, "summary": summary}
                if structure is not None:
                    file_entry["structure"] = structure
                valid_files.append(file_entry)

            if valid_files:
                tree[rel_dir] = valid_files

        self._save_cache()
        log_info("[ProjectScanner] ✅ Сканирование завершено.")
        return tree

    # ----------------- helpers -----------------

    def _should_ignore(self, path: str) -> bool:
        norm = os.path.normpath(path)
        path_parts = set(norm.split(os.sep))
        return bool(IGNORE_FOLDERS & path_parts)

    def _is_valid_file(self, filename: str, dirpath: str) -> bool:
        _, ext = os.path.splitext(filename.lower())
        if ext not in ALLOWED_EXTENSIONS:
            return False
        if filename.startswith("_") or filename.startswith("."):
            return False
        if is_copy_or_temp(filename):
            return False
        if self._should_ignore(dirpath):
            return False
        return True

    def _hash_file(self, path: str) -> str:
        try:
            hasher = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            log_error(f"[ProjectScanner] ❌ Не удалось хэшировать файл {path}: {e}")
            return ""

    def _load_cache(self) -> Dict[str, Any]:
        if not os.path.exists(SCAN_CACHE_PATH):
            return {}
        try:
            with open(SCAN_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_warning(f"[ProjectScanner] ⚠️ Не удалось загрузить кэш: {e}")
            return {}

    def _save_cache(self) -> None:
        os.makedirs(os.path.dirname(SCAN_CACHE_PATH), exist_ok=True)
        try:
            with open(SCAN_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.updated_cache, f, indent=2, ensure_ascii=False)
            log_info("[ProjectScanner] 💾 Кэш успешно обновлён.")
        except Exception as e:
            log_error(f"[ProjectScanner] ❌ Ошибка при сохранении кэша: {e}")

    # ----------------- structure extraction -----------------

    def _structure_full(self, file_path: str, code: str) -> Dict[str, Any]:
        """
        Полная структурная сводка:
          lines, classes(list), functions(list), todos(int), tags(list), status
        AST с fallback на regex.
        """
        lines_total = len(code.splitlines())
        todos = len(re.findall(r"#\s*TODO\b", code, flags=re.IGNORECASE))
        classes: List[str] = []
        functions: List[str] = []
        status = "parsed"

        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except Exception:
            status = "fallback"
            classes = re.findall(r"(?m)^\s*class\s+([A-Za-z_]\w*)", code)
            functions = re.findall(r"(?m)^\s*def\s+([A-Za-z_]\w*)", code)

        if not code.strip():
            status = "empty"

        tags = self._guess_tags(file_path, code, classes, functions)

        return {
            "lines": lines_total,
            "classes": sorted(set(classes)) or None,
            "functions": sorted(set(functions)) or None,
            "todos": todos,
            "tags": sorted(set(tags)) or None,
            "status": status,
        }

    def _structure_legacy(self, full: Dict[str, Any]) -> Dict[str, Any]:
        """
        Компактная структура для обратной совместимости.
        """
        class_names = full.get("classes") or []
        func_names = full.get("functions") or []
        return {
            "lines": full.get("lines") or 0,
            "classes_count": len(class_names),
            "functions_count": len(func_names),
            "class_names": class_names,
            "function_names": func_names,
        }

    def _guess_tags(
        self,
        file_path: str,
        code: str,
        classes: List[str],
        functions: List[str],
    ) -> List[str]:
        tags: List[str] = []
        low_path = file_path.lower()
        base = os.path.basename(low_path)

        # по расположению
        if "/ui/" in low_path or base == "main_window.py":
            tags.append("ui")
            if "PyQt" in code or "Qt" in code:
                tags.append("qt")
        if "/improver/" in low_path:
            tags.append("improver")
        if "/core/" in low_path:
            tags.append("core")
        if "/tests" in low_path or "test" in base:
            tags.append("test")
        if "utils" in base:
            tags.append("utils")
        if base in {"main.py", "app.py"}:
            tags.append("entrypoint")

        # по содержимому
        if "openai" in code.lower():
            tags.append("openai")
        if classes and not functions:
            tags.append("oop-heavy")
        if functions and not classes:
            tags.append("procedural")

        return tags