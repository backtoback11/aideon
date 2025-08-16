# app/modules/improver/meta_summarizer.py

import json
from app.modules.improver.project_scanner import ProjectScanner
from app.logger import log_info

class MetaSummarizer:
    """
    Генерирует метасаммери по всему проекту:
    - Строит карту файлов с метаданными (метасаммери каждого файла)
    - Анализирует структуру, связи, теги, точки входа, модули ядра/расширения
    - Формирует итоговое описание проекта для дальнейшего использования AI
    """

    def __init__(self, root_path="app"):
        self.root_path = root_path
        self.scanner = ProjectScanner(root_path=root_path)
        self.structure = {}
        self.meta_summary = {}

    def build_meta_summary(self):
        """
        Запускает сканер, собирает структуру проекта и строит обобщённое summary.
        """
        log_info("[MetaSummarizer] 🔎 Сбор структуры и метасаммери по проекту...")
        self.structure = self.scanner.scan()
        self.meta_summary = self._build_summary_from_structure(self.structure)
        return self.meta_summary

    def _build_summary_from_structure(self, structure):
        """
        Формирует агрегированное метасаммери по всей структуре проекта.
        """
        all_files = []
        tags_counter = {}
        classes_counter = {}
        functions_counter = {}

        for rel_dir, files in structure.items():
            for file in files:
                summary = file.get("summary", "")
                # Парсим summary для сбора тегов, классов, функций
                tags = self._extract_line(summary, "# 🏷️ Теги:")
                classes = self._extract_line(summary, "# 🧩 Классы:")
                functions = self._extract_line(summary, "# 🪝 Функции:")

                # Счётчики для тегов/классов/функций
                for tag in (tags or "").split(","):
                    tag = tag.strip()
                    if tag:
                        tags_counter[tag] = tags_counter.get(tag, 0) + 1
                for cls in (classes or "").split(","):
                    cls = cls.strip()
                    if cls and cls != '—':
                        classes_counter[cls] = classes_counter.get(cls, 0) + 1
                for func in (functions or "").split(","):
                    func = func.strip()
                    if func and func != '—':
                        functions_counter[func] = functions_counter.get(func, 0) + 1

                all_files.append({
                    "file": f"{rel_dir}/{file['name']}".replace("./", ""),
                    "tags": tags,
                    "classes": classes,
                    "functions": functions,
                    "short_summary": self._extract_description(summary)
                })

        return {
            "files": all_files,
            "tags_summary": tags_counter,
            "classes_summary": classes_counter,
            "functions_summary": functions_counter,
            "project_description": self._auto_project_description(tags_counter, classes_counter, functions_counter)
        }

    def _extract_line(self, summary, marker):
        """Извлекает строку после маркера"""
        for line in summary.splitlines():
            if line.strip().startswith(marker):
                return line.replace(marker, "").strip()
        return ""

    def _extract_description(self, summary):
        """Извлекает краткое описание из summary"""
        started = False
        lines = []
        for line in summary.splitlines():
            if line.startswith("## Краткое описание:"):
                started = True
                continue
            if started:
                if line.strip().startswith("🔍") or line.strip().startswith("# "):
                    break
                lines.append(line.strip())
        return " ".join(lines).strip()

    def _auto_project_description(self, tags_counter, classes_counter, functions_counter):
        """Автоописание структуры проекта на основе собранных данных."""
        parts = []
        if "core" in tags_counter:
            parts.append("В проекте выделены модули ядра (core), обеспечивающие основную логику работы.")
        if "utils" in tags_counter:
            parts.append("Есть вспомогательные утилиты.")
        if "test" in tags_counter:
            parts.append("Обнаружены модули для тестирования.")
        if "config" in tags_counter:
            parts.append("В проекте присутствует конфигурация.")
        parts.append(f"Всего файлов: {sum(tags_counter.values())}. Классов: {len(classes_counter)}. Функций: {len(functions_counter)}.")
        return " ".join(parts)

    def export_json(self, path="app/data/meta_summary.json"):
        """
        Сохраняет итоговое summary в файл для дальнейшего анализа или передачи AI.
        """
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.meta_summary, f, ensure_ascii=False, indent=2)
        log_info(f"[MetaSummarizer] 💾 Метасаммери сохранён: {path}")

# ===============================
# Для запуска отдельно:
# if __name__ == "__main__":
#     ms = MetaSummarizer(root_path="app")
#     summary = ms.build_meta_summary()
#     ms.export_json()
#     print(json.dumps(summary, ensure_ascii=False, indent=2))