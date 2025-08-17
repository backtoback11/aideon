import ast
import re

class FileSummarizer:
    """
    Генерирует метасаммери (meta-summary) для каждого файла:
    - Назначение (ядро/утилита/расширение и т.д.)
    - Список классов, функций, точек входа
    - Краткое описание (выжимка смысла)
    - Автотеги (core, extension, config, etc)
    """

    def summarize(self, file_path: str, file_content: str) -> str:
        # --- 1. AST-анализ структуры файла ---
        classes, functions = self._parse_structure(file_content)
        num_lines = len(file_content.splitlines())

        # --- 2. Автоматические теги по имени файла/структуре ---
        tags = self._infer_tags(file_path, classes, functions)

        # --- 3. Краткое summary ---
        summary_lines = [
            f"# 📁 Путь: {file_path}",
            f"# 👁️ Строк: {num_lines}",
            f"# 🏷️ Теги: {', '.join(tags) if tags else 'none'}",
            f"# 🧩 Классы: {', '.join(classes) if classes else '—'}",
            f"# 🪝 Функции: {', '.join(functions) if functions else '—'}",
            "",
            "## Краткое описание:",
            self._guess_purpose(file_path, file_content, classes, functions),
            "",
            "🔍 Это summary сгенерировано автоматически. Проверь вручную при необходимости."
        ]
        return "\n".join(summary_lines)

    def _parse_structure(self, code: str):
        """AST-парсинг для извлечения классов и функций."""
        classes = []
        functions = []
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    classes.append(node.name)
                elif isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
        except Exception:
            # fallback: простейший re-анализ
            classes = re.findall(r'^class\s+(\w+)', code, re.MULTILINE)
            functions = re.findall(r'^def\s+(\w+)', code, re.MULTILINE)
        return classes, functions

    def _infer_tags(self, file_path, classes, functions):
        """Автотеги по названию файла и структуре."""
        tags = []
        filename = file_path.lower()
        if 'core' in filename or 'main' in filename or filename.endswith('app.py'):
            tags.append('core')
        if 'config' in filename or filename.endswith('.json') or filename.endswith('.cfg'):
            tags.append('config')
        if not classes and not functions:
            tags.append('data' if filename.endswith('.py') else 'unknown')
        if 'test' in filename or 'tests' in filename:
            tags.append('test')
        if 'utils' in filename or 'helper' in filename:
            tags.append('utils')
        # Можно добавить свои эвристики (extension, api, etc)
        return tags

    def _guess_purpose(self, file_path, file_content, classes, functions):
        """Автоописание для summary (можно дополнять под проект)."""
        path = file_path.lower()
        if 'logger' in path:
            return "Модуль для логирования событий, ошибок и информации в проекте."
        if 'scanner' in path:
            return "Сканирует структуру проекта, формирует дерево файлов и summary."
        if 'improver' in path:
            return "Модуль для самоусовершенствования и автогенерации изменений в проекте."
        if 'file_manager' in path or 'manager' in path:
            return "Модуль для управления файлами и их содержимым в проекте."
        if 'analyzer' in path:
            return "Модуль для анализа кода и генерации промтов для AI."
        if classes and not functions:
            return f"Содержит классы: {', '.join(classes)}."
        if functions and not classes:
            return f"Содержит функции: {', '.join(functions)}."
        if not classes and not functions:
            if len(file_content.strip()) < 30:
                return "Пустой или служебный файл."
            return "Содержит код без явных классов и функций."
        return "Python-модуль проекта Aideon. Требует ручного описания для точности."


# 👇 Универсальная функция для вызова саммери
def summarize_code(file_content: str, file_path: str = "unknown.py") -> str:
    return FileSummarizer().summarize(file_path, file_content)