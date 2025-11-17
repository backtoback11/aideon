# app/modules/improver/project_scanner.py
from __future__ import annotations

import os
import ast
import re
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.logger import log_info, log_warning, log_error

# Лёгкая зависимость опциональна в ранних ветках
try:
    from app.modules.improver.file_summarizer import FileSummarizer  # type: ignore
except Exception:
    FileSummarizer = None  # type: ignore

SCAN_CACHE_PATH = os.path.abspath("app/data/scan_cache.json")

# Разрешённые расширения (оставил .py по-умолчанию; при желании дополни)
ALLOWED_EXTENSIONS = {".py"}

# Папки/паттерны, которые исключаем
IGNORE_FOLDERS = {
    "sandbox", "venv", ".venv", "env", "__pycache__", ".git", "site-packages",
    "frontend_old", "tests", "testdata",
    # исключаем внутренние артефакты самоулучшения
    "backups", "patches", ".aideon_backups"
}
IGNORE_PATTERNS = ["копия", "copy", "backup", "tmp", "bak", "~"]

# Лимит размера файла (в КБ), чтобы не валить LLM и не тормозить скан
MAX_FILE_KB = 1024  # 1 МБ


def _is_hidden(name: str) -> bool:
    return name.startswith(".") or name.startswith("_")


def _is_copy_or_temp(name: str) -> bool:
    low = name.lower()
    return any(pat in low for pat in IGNORE_PATTERNS)


def _split_ext_lower(path: str) -> Tuple[str, str]:
    base, ext = os.path.splitext(path)
    return base, ext.lower()


class ProjectScanner:
    """
    🔍 Сканирует проект (по-умолчанию 'app') c кэшированием метасаммери.
    Возвращаемая структура:
      {
        "<rel_dir>": [
          {
            "name": "main_window.py",
            "rel_dir": "ui",                              # без префикса app/
            "rel_path": "app/ui/main_window.py",         # нормализованный относительный путь
            "abs_path": "/abs/.../app/ui/main_window.py",
            "size": 12345,
            "ext": ".py",
            "summary": { ... богатая сводка ... },
            "structure": { ... legacy компакт ... },
            "skipped": False,
            "reason": None
          },
          ...
        ]
      }
    """

    def __init__(self, root_path: str = "app"):
        # Нормализуем корень
        self.root_path = os.path.abspath(root_path)
        if os.path.basename(self.root_path) != "app":
            # защищаемся от двойного app/app
            candidate = os.path.join(self.root_path, "app")
            if os.path.isdir(candidate):
                self.root_path = os.path.abspath(candidate)

        self.cache: Dict[str, Any] = self._load_cache()
        self.updated_cache: Dict[str, Any] = {}
        self.summarizer = FileSummarizer() if FileSummarizer else None

    # -------------------- ПУБЛИЧНОЕ АПИ --------------------

    def scan(self) -> Dict[str, List[Dict[str, Any]]]:
        log_info(f"[ProjectScanner] 🔍 Начало сканирования директории: {self.root_path}")
        tree: Dict[str, List[Dict[str, Any]]] = {}
        total_files = 0

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Фильтруем поддиректории inplace
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore_dir(os.path.join(dirpath, d))
                and not _is_hidden(d)
                and not _is_copy_or_temp(d)
            ]

            rel_dir = os.path.relpath(dirpath, self.root_path)
            if rel_dir == ".":
                rel_dir = ""  # корень 'app' → пустая строка для красивых путей
            bucket: List[Dict[str, Any]] = []

            for fname in filenames:
                abs_path = os.path.join(dirpath, fname)
                base, ext = _split_ext_lower(fname)

                # Фильтры на файл
                reason = self._file_skip_reason(fname=fname, dirpath=dirpath, ext=ext)
                if reason:
                    # пропуск без лог-спама — это норма
                    continue

                size = self._safe_size(abs_path)
                if size is None:
                    log_warning(f"[ProjectScanner] ⚠️ Не удалось получить размер: {abs_path}")
                    continue
                if (size / 1024.0) > MAX_FILE_KB:
                    # слишком большой — игнорируем
                    continue

                # Ключ для кэша: быстрый (size + mtime) + sha256 при изменении
                mtime = self._safe_mtime(abs_path)
                fast_key = f"{size}:{int(mtime or 0)}"

                cached = self.cache.get(abs_path)
                cache_key = cached.get("fast_key") if isinstance(cached, dict) else None

                # Если быстрый ключ совпал → используем кэш как есть
                if cached and cache_key == fast_key:
                    summary = cached.get("summary")
                    structure = cached.get("structure")
                    # Бэк-компат для старых строковых summary
                    if isinstance(summary, str):
                        summary = self._wrap_legacy_summary(summary)
                    self._touch_cache(abs_path, fast_key, summary, structure)
                    log_info(f"[ProjectScanner] ⚡ Кэш использован для: {fname}")
                else:
                    # Иначе — считаем sha и заново строим
                    file_hash = self._sha256(abs_path)
                    text = self._read_text(abs_path)
                    if text is None:
                        log_warning(f"[ProjectScanner] ⚠️ Ошибка чтения файла: {abs_path}")
                        continue

                    raw_summary = self._call_summarizer(abs_path, text)
                    full_struct = self._structure_full(abs_path, text)
                    summary = {**full_struct, "raw_summary": raw_summary}
                    structure = self._structure_legacy(full_struct)

                    self._write_cache(abs_path, fast_key, file_hash, summary, structure)
                    log_info(f"[ProjectScanner] 📄 Новый метасаммери: {fname}")

                rel_path = self._build_rel_path(rel_dir, fname)   # "app/<rel_dir>/fname"
                file_entry: Dict[str, Any] = {
                    "name": fname,
                    "rel_dir": rel_dir,
                    "rel_path": rel_path,
                    "abs_path": abs_path,
                    "size": size,
                    "ext": ext,
                    "summary": summary,
                    "structure": structure,
                    "skipped": False,
                    "reason": None,
                }
                bucket.append(file_entry)
                total_files += 1

            if bucket:
                tree[rel_dir] = bucket

        self._save_cache()
        log_info(f"[ProjectScanner] ✅ Сканирование завершено. Файлов к обработке: {total_files}")
        return tree

    # -------------------- CACHE --------------------

    def _load_cache(self) -> Dict[str, Any]:
        if not os.path.exists(SCAN_CACHE_PATH):
            return {}
        try:
            with open(SCAN_CACHE_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
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

    def _touch_cache(self, abs_path: str, fast_key: str, summary: Any, structure: Any) -> None:
        self.updated_cache[abs_path] = {
            "fast_key": fast_key,
            "hash": None,  # может быть не нужен, если fast_key совпал
            "summary": summary,
            "structure": structure,
            "timestamp": datetime.now().isoformat(),
        }

    def _write_cache(self, abs_path: str, fast_key: str, file_hash: Optional[str],
                     summary: Any, structure: Any) -> None:
        self.updated_cache[abs_path] = {
            "fast_key": fast_key,
            "hash": file_hash,
            "summary": summary,
            "structure": structure,
            "timestamp": datetime.now().isoformat(),
        }

    # -------------------- FILE / PATH HELPERS --------------------

    def _should_ignore_dir(self, abs_dir: str) -> bool:
        # Сравниваем по сегментам пути
        norm = os.path.normpath(abs_dir)
        parts = set(norm.split(os.sep))
        return bool(IGNORE_FOLDERS & parts)

    def _file_skip_reason(self, fname: str, dirpath: str, ext: str) -> Optional[str]:
        if ext not in ALLOWED_EXTENSIONS:
            return "ext"
        if _is_hidden(fname):
            return "hidden"
        if _is_copy_or_temp(fname):
            return "temp"
        if self._should_ignore_dir(dirpath):
            return "ignored_dir"
        return None

    def _safe_size(self, abs_path: str) -> Optional[int]:
        try:
            return os.path.getsize(abs_path)
        except Exception:
            return None

    def _safe_mtime(self, abs_path: str) -> Optional[float]:
        try:
            return os.path.getmtime(abs_path)
        except Exception:
            return None

    def _read_text(self, abs_path: str) -> Optional[str]:
        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception:
            # пробуем без указания encoding
            try:
                with open(abs_path, "r") as f:
                    return f.read()
            except Exception:
                return None

    def _sha256(self, abs_path: str) -> Optional[str]:
        try:
            h = hashlib.sha256()
            with open(abs_path, "rb") as f:
                for chunk in iter(lambda: f.read(8192), b""):
                    h.update(chunk)
            return h.hexdigest()
        except Exception as e:
            log_error(f"[ProjectScanner] ❌ Не удалось хэшировать файл {abs_path}: {e}")
            return None

    def _build_rel_path(self, rel_dir: str, fname: str) -> str:
        # rel_dir приходит уже БЕЗ 'app/'. Здесь гарантируем "app/<rel_dir>/fname"
        rel_dir = rel_dir.lstrip("/\\")
        if rel_dir == "":
            return os.path.join("app", fname).replace("\\", "/")
        return os.path.join("app", rel_dir, fname).replace("\\", "/")

    # -------------------- SUMMARY / STRUCTURE --------------------

    def _call_summarizer(self, file_path: str, content: str) -> str:
        if self.summarizer is None:
            # Мягкая деградация на старых ветках
            return "(summarizer disabled)"
        try:
            return self.summarizer.summarize(file_path, content)
        except Exception as e:
            return f"(summarizer error: {e})"

    def _wrap_legacy_summary(self, text: str) -> Dict[str, Any]:
        return {
            "lines": None,
            "classes": None,
            "functions": None,
            "todos": 0,
            "tags": None,
            "status": "legacy",
            "raw_summary": text,
        }

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
        if f"{os.sep}ui{os.sep}" in low_path or base == "main_window.py":
            tags.append("ui")
            if "PyQt" in code or "Qt" in code:
                tags.append("qt")
        if f"{os.sep}improver{os.sep}" in low_path:
            tags.append("improver")
        if f"{os.sep}core{os.sep}" in low_path:
            tags.append("core")
        if f"{os.sep}tests" in low_path or "test" in base:
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

        return sorted(set(tags))