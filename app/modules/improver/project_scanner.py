import os
import hashlib
import json
from datetime import datetime

from app.logger import log_info, log_warning, log_error
from app.modules.improver.file_summarizer import FileSummarizer

SCAN_CACHE_PATH = "app/data/scan_cache.json"
ALLOWED_EXTENSIONS = {".py"}

IGNORE_FOLDERS = {
    "sandbox", "venv", ".venv", "env", "__pycache__", ".git", "site-packages", "frontend_old", "tests", "testdata"
}
IGNORE_PATTERNS = [
    "копия", "copy", "backup", "tmp", "bak", "~"
]

def is_hidden(filename):
    return filename.startswith('.') or filename.startswith('_')

def is_copy_or_temp(filename):
    low = filename.lower()
    return any(pat in low for pat in IGNORE_PATTERNS)

class ProjectScanner:
    """
    🔍 Сканирует структуру проекта Aideon, исключая sandbox, venv, копии и временные файлы/каталоги.
    Формирует дерево файлов с метасаммери по каждому файлу, кэширует обработку для ускорения последующих запусков.
    """

    def __init__(self, root_path="app"):
        self.root_path = os.path.abspath(root_path)
        self.cache = self._load_cache()
        self.updated_cache = {}
        self.summarizer = FileSummarizer()

    def scan(self):
        log_info(f"[ProjectScanner] 🔍 Начало сканирования директории: {self.root_path}")
        tree = {}

        for dirpath, dirnames, filenames in os.walk(self.root_path):
            # Фильтрация поддиректорий in-place
            dirnames[:] = [
                d for d in dirnames
                if not self._should_ignore(os.path.join(dirpath, d))
                and not is_hidden(d)
                and not is_copy_or_temp(d)
            ]
            rel_dir = os.path.relpath(dirpath, self.root_path)
            valid_files = []

            for fname in filenames:
                if not self._is_valid_file(fname, dirpath):
                    continue

                full_path = os.path.join(dirpath, fname)
                file_hash = self._hash_file(full_path)

                # Использование кэша для неизменённых файлов
                if full_path in self.cache and self.cache[full_path]["hash"] == file_hash:
                    summary = self.cache[full_path]["summary"]
                    log_info(f"[ProjectScanner] ⚡ Кэш использован для: {fname}")
                else:
                    try:
                        with open(full_path, "r", encoding="utf-8") as f:
                            content = f.read()
                        summary = self.summarizer.summarize(full_path, content)
                        log_info(f"[ProjectScanner] 📄 Новый метасаммери: {fname}")
                    except Exception as e:
                        log_warning(f"[ProjectScanner] ⚠️ Ошибка при чтении {fname}: {e}")
                        continue

                self.updated_cache[full_path] = {
                    "hash": file_hash,
                    "summary": summary,
                    "timestamp": datetime.now().isoformat()
                }
                valid_files.append({"name": fname, "summary": summary})

            if valid_files:
                tree[rel_dir] = valid_files

        self._save_cache()
        log_info("[ProjectScanner] ✅ Сканирование завершено.")
        return tree

    def _should_ignore(self, path):
        """
        Проверяет, содержит ли путь хотя бы одну игнорируемую папку (рекурсивно).
        """
        norm = os.path.normpath(path)
        path_parts = set(norm.split(os.sep))
        return bool(IGNORE_FOLDERS & path_parts)

    def _is_valid_file(self, filename, dirpath):
        """
        Проверяет, допустим ли файл к анализу (по расширению, скрытый, копия, не в игнорируемой папке).
        """
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

    def _hash_file(self, path):
        try:
            hasher = hashlib.sha256()
            with open(path, "rb") as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            log_error(f"[ProjectScanner] ❌ Не удалось хэшировать файл {path}: {e}")
            return ""

    def _load_cache(self):
        if not os.path.exists(SCAN_CACHE_PATH):
            return {}
        try:
            with open(SCAN_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            log_warning(f"[ProjectScanner] ⚠️ Не удалось загрузить кэш: {e}")
            return {}

    def _save_cache(self):
        os.makedirs(os.path.dirname(SCAN_CACHE_PATH), exist_ok=True)
        try:
            with open(SCAN_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.updated_cache, f, indent=2, ensure_ascii=False)
            log_info("[ProjectScanner] 💾 Кэш успешно обновлён.")
        except Exception as e:
            log_error(f"[ProjectScanner] ❌ Ошибка при сохранении кэша: {e}")