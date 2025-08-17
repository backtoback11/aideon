import json
import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton,
    QListWidget, QMessageBox
)

class PanelHistory(QWidget):
    def __init__(self, history_path="app/logs/history.json", parent=None):
        """
        Панель истории (исправлений, тестов, загрузок проектов и т.д.).
        """
        super().__init__(parent)
        self.history_path = history_path
        self.history = self._load_history()  # Загружаем историю при запуске
        self._init_ui()
        self.load_history()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("История действий, исправлений и тестов")
        layout.addWidget(self.label)

        # Список записей истории
        self.history_list = QListWidget()
        self.history_list.itemClicked.connect(self.show_details)
        layout.addWidget(self.history_list)

        # Поле вывода деталей
        self.details_output = QTextEdit()
        self.details_output.setReadOnly(True)
        layout.addWidget(self.details_output)

        # Кнопка для сравнения исправлений (diff)
        self.compare_button = QPushButton("Сравнить исправления (diff)")
        self.compare_button.setEnabled(False)
        self.compare_button.clicked.connect(self.compare_fixes)
        layout.addWidget(self.compare_button)

        # Кнопка для очистки истории
        self.clear_button = QPushButton("Очистить историю")
        self.clear_button.clicked.connect(self.clear_history)
        layout.addWidget(self.clear_button)

        self.setLayout(layout)

    def load_history(self):
        """
        Загружает историю и формирует список (history_list).
        """
        self.history_list.clear()

        if not self.history:
            self.history_list.addItem("История пуста.")
            return

        for i, entry in enumerate(self.history):
            action = entry.get("action", "unknown")
            timestamp = entry.get("time") or entry.get("timestamp") or ""
            # Формируем строку вида "1. project_loaded (2023-09-01T12:00:00)"
            item_str = f"{i+1}. {action}"
            if timestamp:
                item_str += f" ({timestamp})"

            self.history_list.addItem(item_str)

    def show_details(self, item):
        """
        Показывает детали записи истории в details_output.
        """
        index = self.history_list.row(item)
        if index < 0 or index >= len(self.history):
            return

        entry = self.history[index]
        action = entry.get("action", "unknown")

        # Собираем HTML для details_output
        html = f"<b>Действие:</b> {action}\n\n"

        if action == "project_loaded":
            # Пример: {"action":"project_loaded","project_path":"...","project_tree":{...}}
            project_path = entry.get("project_path", "Неизвестно")
            project_tree = entry.get("project_tree", {})
            html += f"<b>Загружен проект:</b> {project_path}\n\n"
            html += (
                f"<b>Структура проекта:</b>\n"
                f"{json.dumps(project_tree, indent=2, ensure_ascii=False)}"
            )

        elif action == "analyze_chunk":
            # Пример: {"action":"analyze_chunk","files":["sub/a.py"],"ai_response":"..."}
            files = entry.get("files", [])
            html += f"<b>Файлы в этом шаге:</b>\n"
            for f in files:
                html += f" - {f}\n"
            ai_resp = entry.get("ai_response", "")
            if ai_resp:
                html += f"\n<b>Ответ AI:</b>\n{ai_resp}"

        elif action == "fix_applied":
            # Пример: {"action":"fix_applied","file":"...","diff":"...","time":"..."}
            file_name = entry.get("file", "Неизвестный файл")
            diff = entry.get("diff", "Нет `diff`-разницы.")
            html += f"<b>Исправлен файл:</b> {file_name}\n\n"
            html += f"<b>Разница (diff):</b>\n{diff}"

        else:
            # Старый формат (run_test, прочие)
            file_name = entry.get("file", "Неизвестный файл")
            stdout = entry.get("stdout", "")
            stderr = entry.get("stderr", "")
            diff = entry.get("diff", "Нет `diff`-разницы.")
            return_code = entry.get("return_code", None)

            html += f"<b>Файл:</b> {file_name}\n\n"
            if stdout:
                html += f"<b>Вывод теста:</b>\n{stdout}\n\n"
            if stderr:
                html += f"<b>Ошибки:</b>\n{stderr}\n\n"
            if isinstance(return_code, int):
                status_str = "Успешно" if return_code == 0 else "Ошибка"
                html += f"<b>Статус:</b> {status_str}\n\n"
            if diff != "Нет `diff`-разницы.":
                html += f"<b>Разница (diff):</b>\n{diff}"

        self.details_output.setHtml(html)

        # Активировать "Сравнить исправления" только при наличии diff
        diff_val = entry.get("diff", "")
        if diff_val and diff_val.strip() != "Нет `diff`-разницы.":
            self.compare_button.setEnabled(True)
        else:
            self.compare_button.setEnabled(False)

    def compare_fixes(self):
        """
        Показывает diff, если он есть, в отдельном QMessageBox.
        """
        selected_item = self.history_list.currentItem()
        if not selected_item:
            QMessageBox.warning(self, "Ошибка", "Выберите запись в истории для сравнения.")
            return

        index = self.history_list.row(selected_item)
        if index < 0 or index >= len(self.history):
            return

        entry = self.history[index]
        diff = entry.get("diff", "Нет `diff`-разницы.")
        QMessageBox.information(self, "Сравнение исправлений", f"Разница:\n\n{diff}")

    def clear_history(self):
        """
        Очищает историю (history.json).
        """
        confirm = QMessageBox.question(
            self,
            "Очистка истории",
            "Вы уверены, что хотите удалить всю историю?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm == QMessageBox.StandardButton.Yes:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump([], f, indent=4, ensure_ascii=False)
            self.history.clear()
            self.history_list.clear()
            self.details_output.clear()

    def _load_history(self):
        """
        Загружает историю (список записей) из JSON.
        Если файл повреждён или пуст — возвращаем [].
        """
        if not os.path.exists(self.history_path):
            return []

        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError:
            print("⚠️ Ошибка загрузки истории: файл повреждён. Очищаем history.json.")
            # Перезаписываем пустой массив, чтобы файл не оставался битым
            with open(self.history_path, "w", encoding="utf-8") as wf:
                json.dump([], wf, indent=4, ensure_ascii=False)
            return []
        except Exception as e:
            print(f"⚠️ Неизвестная ошибка при чтении истории: {e}")
            return []