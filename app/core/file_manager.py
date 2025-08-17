import os
import shutil
import json
from PyQt6.QtWidgets import QFileDialog

# Набор исключаемых директорий
EXCLUDED_DIRS = {
    "venv", ".git", "__pycache__", "node_modules", "dist", "build",
    "site-packages", ".idea", ".vs", ".vscode",
    "sandbox"  # Чтобы не копировать саму себя
}

# Набор исключаемых расширений
EXCLUDED_EXTS = {
    ".pyc", ".pyo", ".log", ".exe", ".dll", ".so", ".dylib",
    ".zip", ".rar", ".7z", ".tar", ".gz"
}

# Пример ограничения размера (в байтах)
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB

# Ограничение на длину пути (примерно)
MAX_PATH_LENGTH = 250


class FileManager:
    def __init__(self, sandbox_path="app/sandbox", history_path="app/logs/history.json"):
        """
        Управляет загрузкой файлов / проектов в песочницу (sandbox),
        формирует и сохраняет структуру проекта, ведёт историю загрузок.
        """
        self.sandbox_path = os.path.abspath(sandbox_path)
        self.history_path = history_path
        self.project_tree_path = "app/logs/project_tree.json"

        os.makedirs(self.sandbox_path, exist_ok=True)
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

        self._original_project_root = None  # Запоминаем корень исходного проекта

    # ---------------------------------------------------------
    # Диалоги выбора (файл / проект)
    # ---------------------------------------------------------
    def open_file_dialog(self, multiple=False):
        """Вызывает системный диалог выбора файлов."""
        if multiple:
            files, _ = QFileDialog.getOpenFileNames(
                None,
                "Выберите файлы для анализа",
                "",
                "Все файлы (*);;Python Files (*.py)"
            )
            return files or []
        else:
            file_path, _ = QFileDialog.getOpenFileName(
                None,
                "Выберите файл для анализа",
                "",
                "Все файлы (*);;Python Files (*.py)"
            )
            return [file_path] if file_path else []

    def open_project_dialog(self):
        """Открывает диалог выбора папки проекта, копирует её в sandbox (с фильтрацией)."""
        project_path = QFileDialog.getExistingDirectory(None, "Выберите проект для анализа")
        if not project_path:
            print("[FileManager] Пользователь отменил выбор проекта.")
            return None

        project_path = os.path.abspath(project_path)
        print(f"[FileManager] Исходный проект: {project_path}")

        if project_path.startswith(self.sandbox_path):
            print("[FileManager] Предупреждение: проект уже внутри sandbox. Копирование отменено.")
            return None

        destination = os.path.join(self.sandbox_path, os.path.basename(project_path))
        destination = os.path.abspath(destination)
        print(f"[FileManager] Копируем проект в sandbox: {destination}")

        # Удаляем старый проект, если есть
        if os.path.exists(destination):
            print(f"[FileManager] Удаляем старую копию: {destination}")
            shutil.rmtree(destination)

        # Запоминаем корневой путь (для _ignore_filter)
        self._original_project_root = project_path

        try:
            shutil.copytree(
                src=project_path,
                dst=destination,
                ignore=self._ignore_filter  # Используем встроенный ignore
            )
            print("[FileManager] Проект скопирован (copytree).")
        except Exception as e:
            # Логируем, но всё равно продолжаем (папка может быть частично скопирована)
            print(f"[FileManager] Ошибка при копировании проекта: {e}")
            # Можно при желании вернуть None, если считаем операцию провальной
            # Но если хотим «частично» считать её успешной, не прерываем

        # Сохраняем структуру (того, что успели скопировать)
        self._save_project_tree(destination)
        # Запись в history.json
        self._save_to_history(destination, is_project=True)
        print("[FileManager] Проект обработан, даже если были ошибки. Возвращаем destination.")
        return destination

    # ---------------------------------------------------------
    # Загрузка одиночного файла
    # ---------------------------------------------------------
    def save_file(self, source_path):
        """Копирует файл в sandbox, логирует ошибку, но не прерывает всю работу."""
        if not source_path:
            print("[FileManager] save_file: Путь к файлу пуст.")
            return None

        source_path = os.path.abspath(source_path)
        filename = os.path.basename(source_path)
        destination = os.path.join(self.sandbox_path, filename)
        destination = os.path.abspath(destination)

        print(f"[FileManager] save_file копирование: {source_path} → {destination}")

        try:
            if self._too_long_path(destination):
                print(f"[FileManager] Путь слишком длинный: {destination}")
                return None

            if source_path.startswith(self.sandbox_path):
                print("[FileManager] Файл уже в sandbox, пропускаем копирование.")
                return None

            shutil.copy2(source_path, destination)
            self._save_to_history(destination, is_project=False)
            print("[FileManager] Файл скопирован в sandbox.")
            return destination
        except Exception as e:
            print(f"[FileManager] Ошибка при копировании файла: {e}")
            return None

    # ---------------------------------------------------------
    # Чтение / список / удаление
    # ---------------------------------------------------------
    def read_file(self, file_path):
        if not file_path or not os.path.exists(file_path):
            print(f"[FileManager] read_file: Файл не найден: {file_path}")
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = f.read()
            print(f"[FileManager] Файл прочитан: {file_path}")
            return data
        except Exception as e:
            print(f"[FileManager] Ошибка при чтении файла '{file_path}': {e}")
            return None

    def list_files(self):
        """Список (файлов и папок) на верхнем уровне sandbox."""
        try:
            items = os.listdir(self.sandbox_path)
            print(f"[FileManager] Содержимое sandbox: {items}")
            return items
        except Exception as e:
            print(f"[FileManager] Ошибка при list_files: {e}")
            return []

    def delete_file(self, filename):
        """Удаляет файл/папку из sandbox + запись из history. Возвращает bool."""
        file_path = os.path.join(self.sandbox_path, filename)
        file_path = os.path.abspath(file_path)

        if os.path.exists(file_path):
            print(f"[FileManager] Удаляем: {file_path}")
            try:
                if os.path.isdir(file_path):
                    shutil.rmtree(file_path)
                else:
                    os.remove(file_path)
                self._remove_from_history(file_path)
                return True
            except Exception as e:
                print(f"[FileManager] Ошибка удаления '{file_path}': {e}")
                return False
        else:
            print(f"[FileManager] delete_file: Нет такого файла/папки: {file_path}")
            return False

    # ---------------------------------------------------------
    # История (history.json)
    # ---------------------------------------------------------
    def _save_to_history(self, path, is_project=False):
        """Добавляем запись (path, type=file/project) в history.json, если её нет."""
        history = self._load_history()
        known_paths = {h["path"] for h in history}
        if path not in known_paths:
            entry_type = "project" if is_project else "file"
            print(f"[FileManager] Добавляем в history: {path} (type={entry_type})")
            history.append({
                "path": path,
                "type": entry_type
            })
            try:
                with open(self.history_path, "w", encoding="utf-8") as f:
                    json.dump(history, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[FileManager] Ошибка записи history.json: {e}")

    def _load_history(self):
        if not os.path.exists(self.history_path):
            return []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[FileManager] Ошибка при чтении history.json: {e}")
            return []

    def _remove_from_history(self, file_path):
        history = self._load_history()
        new_hist = [x for x in history if x["path"] != file_path]
        if len(new_hist) != len(history):
            print(f"[FileManager] Удаляем из history: {file_path}")
            try:
                with open(self.history_path, "w", encoding="utf-8") as f:
                    json.dump(new_hist, f, indent=4, ensure_ascii=False)
            except Exception as e:
                print(f"[FileManager] Ошибка записи history.json: {e}")

    # ---------------------------------------------------------
    # Сохранение структуры проекта (project_tree.json)
    # ---------------------------------------------------------
    def _save_project_tree(self, project_path):
        """Сканируем скопированный проект, записываем структуру в project_tree.json."""
        project_tree = self.get_project_tree(project_path)
        print(f"[FileManager] Сохраняем структуру проекта в: {self.project_tree_path}")
        try:
            with open(self.project_tree_path, "w", encoding="utf-8") as f:
                json.dump(project_tree, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[FileManager] Ошибка при сохранении project_tree.json: {e}")

    def get_project_tree(self, project_path="app"):
        """
        Возвращает структуру каталогов (dict):
        {
          ".": [...файлы...],
          "subdir": [...],
          ...
        }
        Пропускаем нежелательные dirs/files.
        """
        project_path = os.path.abspath(project_path)
        out_tree = {}

        for root, dirs, files in os.walk(project_path):
            # Фильтруем dirs, чтобы не заходить в EXCLUDED_DIRS
            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]

            valid_files = []
            for f in files:
                if not self._should_skip_file(f, root_dir=root):
                    valid_files.append(f)

            rel_path = os.path.relpath(root, project_path)
            out_tree[rel_path] = valid_files

        return out_tree

    # ---------------------------------------------------------
    # Фильтрация (copytree ignore=...) и общие методы
    # ---------------------------------------------------------
    def _ignore_filter(self, dir_path, items):
        """
        Функция для copytree(ignore=...).
        Возвращаем список имён, которые надо игнорировать (не копировать).
        """
        ignored = []

        # Если не задано, считаем dir_path корнем
        if not self._original_project_root:
            self._original_project_root = dir_path

        for name in items:
            full_path = os.path.join(dir_path, name)
            rel = os.path.relpath(full_path, self._original_project_root)
            potential_dest = os.path.join(self.sandbox_path, rel)

            # Проверяем длину пути
            if self._too_long_path(potential_dest):
                print(f"[FileManager] Пропускаем '{name}' (слишком длинный путь).")
                ignored.append(name)
                continue

            # Проверяем dirs
            if os.path.isdir(full_path):
                if self._should_skip_dir(name):
                    print(f"[FileManager] Пропускаем директорию: '{name}'")
                    ignored.append(name)
            else:
                # Файлы по расширению, размеру
                if self._should_skip_file(name, root_dir=dir_path):
                    print(f"[FileManager] Пропускаем файл: '{name}'")
                    ignored.append(name)

        return ignored

    def _should_skip_dir(self, dirname):
        return dirname.lower() in EXCLUDED_DIRS

    def _should_skip_file(self, filename, root_dir=None):
        _, ext = os.path.splitext(filename.lower())
        if ext in EXCLUDED_EXTS:
            return True

        if root_dir:
            full_path = os.path.join(root_dir, filename)
            if os.path.isfile(full_path):
                size = os.path.getsize(full_path)
                if size > MAX_FILE_SIZE:
                    print(f"[FileManager] _should_skip_file: '{full_path}' (размер {size} > {MAX_FILE_SIZE}).")
                    return True
        return False

    def _too_long_path(self, path_str):
        return len(path_str) > MAX_PATH_LENGTH