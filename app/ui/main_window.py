import os
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMenuBar,
    QPushButton, QTextEdit, QHBoxLayout, QLabel, QSplitter, QTabWidget, QInputDialog, QMessageBox
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QSettings, Qt

from .chat_panel import ChatPanel
from app.modules.self_improver import SelfImprover
from app.modules.improver.project_scanner import ProjectScanner
from app.modules.analyzer import CodeAnalyzer

class SelfImproverPanel(QWidget):
    """
    Правая панель: модуль саморазвития (SelfImprover) — ручной режим + стоп + метасаммери +
    вкладки: идеи AI, история изменений, задачи/запросы.
    """
    def __init__(self, config, chat_panel=None, parent=None):
        super().__init__(parent)
        self.config = config
        self.chat_panel = chat_panel
        self.improver = SelfImprover(config, chat_panel=chat_panel)
        self.generator = None
        self.stopped = False
        self._init_ui()

        self.code_analyzer = CodeAnalyzer(config)
        self.project_scanner = ProjectScanner(root_path="app")
        self.meta_summary_cache = None

        # Для вкладки AI-идей
        self.ai_ideas = []
        # Для истории изменений
        self.history = []
        # Для задач
        self.tasks = []

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)

        # Логи процесса улучшения
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setStyleSheet("background-color: #f9f9f9; font-family: monospace;")
        self.tabs.addTab(self.log_output, "Процесс улучшения")

        # Метасаммери по проекту
        self.meta_output = QTextEdit()
        self.meta_output.setReadOnly(True)
        self.meta_output.setStyleSheet("background-color: #eef5fa; font-family: monospace;")
        self.tabs.addTab(self.meta_output, "📊 Метасаммери проекта")

        # AI-идеи (экспансия)
        self.ai_ideas_output = QTextEdit()
        self.ai_ideas_output.setReadOnly(True)
        self.ai_ideas_output.setStyleSheet("background-color: #e8faef; font-family: monospace;")
        self.tabs.addTab(self.ai_ideas_output, "💡 AI-идеи/Экспансия")

        # История изменений
        self.history_output = QTextEdit()
        self.history_output.setReadOnly(True)
        self.history_output.setStyleSheet("background-color: #f5f0e6; font-family: monospace;")
        self.tabs.addTab(self.history_output, "🕓 История изменений")

        # Запросы/Задачи
        self.tasks_output = QTextEdit()
        self.tasks_output.setReadOnly(True)
        self.tasks_output.setStyleSheet("background-color: #f4eaff; font-family: monospace;")
        self.tabs.addTab(self.tasks_output, "📝 Запросы/Задачи")

        layout.addWidget(QLabel("🤖 Саморазвитие Aideon"))
        layout.addWidget(self.tabs)

        btn_row = QHBoxLayout()
        self.run_btn = QPushButton("🔧 Запустить самоулучшение")
        self.run_btn.clicked.connect(self.start_manual_improvement)
        btn_row.addWidget(self.run_btn)

        self.next_btn = QPushButton("➡️ Далее")
        self.next_btn.setEnabled(False)
        self.next_btn.clicked.connect(self.do_next_step)
        btn_row.addWidget(self.next_btn)

        self.stop_btn = QPushButton("🛑 Стоп")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_process)
        btn_row.addWidget(self.stop_btn)

        self.meta_btn = QPushButton("📊 Метасаммери проекта")
        self.meta_btn.clicked.connect(self.show_meta_summary)
        btn_row.addWidget(self.meta_btn)

        self.add_idea_btn = QPushButton("💡+ AI-идея (вручную)")
        self.add_idea_btn.clicked.connect(self.add_ai_idea)
        btn_row.addWidget(self.add_idea_btn)

        self.auto_idea_btn = QPushButton("🤖 AI-сгенерировать идею")
        self.auto_idea_btn.clicked.connect(self.generate_ai_idea)
        btn_row.addWidget(self.auto_idea_btn)

        self.add_task_btn = QPushButton("📝+ Задача")
        self.add_task_btn.clicked.connect(self.add_task)
        btn_row.addWidget(self.add_task_btn)

        self.auto_task_btn = QPushButton("🤖 AI-задача по саммери")
        self.auto_task_btn.clicked.connect(self.generate_ai_task)
        btn_row.addWidget(self.auto_task_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    def start_manual_improvement(self):
        self.tabs.setCurrentWidget(self.log_output)
        self.log_output.append("▶️ Запуск процесса самоулучшения...\n")
        self.generator = self.improver.run_self_improvement()
        self.stopped = False
        self.run_btn.setEnabled(False)
        self.next_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.do_next_step()

    def do_next_step(self):
        if self.stopped or not self.generator:
            self.log_output.append("🛑 Процесс был остановлен пользователем.\n")
            self.reset_buttons()
            return
        try:
            step = next(self.generator)
            self.log_output.append(step)
            self.history.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {step}")
            self.update_history_tab()
            if "завершено" in step or "Завершено" in step:
                self.reset_buttons()
        except StopIteration:
            self.log_output.append("🟢 Самоулучшение завершено.\n")
            self.reset_buttons()
        except ValueError:
            self.log_output.append("⚠️ Ошибка: попытка повторного шага до завершения предыдущего.\n")
            self.reset_buttons()

    def stop_process(self):
        self.stopped = True
        self.next_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        # Передаём в модуль признак остановки
        try:
            self.improver.stop_requested = True
        except Exception:
            pass
        self.log_output.append("🛑 Самоулучшение остановлено пользователем.\n")

    def reset_buttons(self):
        self.next_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.run_btn.setEnabled(True)
        self.generator = None
        self.stopped = False

    def show_meta_summary(self):
        """
        Формирует и выводит метасаммери по всем .py файлам проекта.
        """
        self.tabs.setCurrentWidget(self.meta_output)
        self.meta_output.clear()
        self.meta_output.append("📊 <b>Метасаммери по всем файлам проекта:</b>\n")
        scanner = self.project_scanner
        tree = scanner.scan()
        self.meta_summary_cache = tree
        for rel_dir, files in tree.items():
            self.meta_output.append(f"\n=== 📂 <b>{rel_dir}</b> ===")
            for f in files:
                summary = f['summary']
                if isinstance(summary, dict):
                    import pprint
                    summary_str = pprint.pformat(summary, compact=True, width=100)
                else:
                    summary_str = str(summary)
                self.meta_output.append(f"\n<b>{f['name']}</b>:\n{summary_str}\n{'-'*50}")

    def add_ai_idea(self):
        idea, ok = QInputDialog.getText(self, "Добавить AI-идею", "Опишите идею/фичу для AI:")
        if ok and idea.strip():
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
            self.ai_ideas.append(entry)
            self.update_ai_ideas_tab()

    def generate_ai_idea(self):
        """
        Генерирует идею на основе текущих summary и отправляет её в AI-идеи.
        """
        # Используем кэш, если уже строили метасаммери
        if not self.meta_summary_cache:
            self.show_meta_summary()
        prompt = (
            "Проанализируй следующие summary файлов проекта и предложи одну идею или модуль,"
            " который значительно усилит, ускорит или расширит возможности системы."
            "\n\nСписок summary по файлам:\n"
        )
        text_summary = ""
        for rel_dir, files in (self.meta_summary_cache or {}).items():
            for f in files:
                summary = f['summary']
                summary_str = summary if isinstance(summary, str) else str(summary)
                text_summary += f"{f['name']}: {summary_str}\n"
        prompt += text_summary + "\n\nОтветь кратко, одна идея:"
        idea = self.code_analyzer.chat(prompt, system_msg="Ты — архитектор новых AI-модулей.")
        entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
        self.ai_ideas.append(entry)
        self.update_ai_ideas_tab()
        QMessageBox.information(self, "AI-идея получена", f"AI-идея:\n{idea.strip()}")

    def update_ai_ideas_tab(self):
        self.ai_ideas_output.clear()
        self.ai_ideas_output.append("💡 <b>AI-идеи/экспансия (ручные и AI-подсказки):</b>\n")
        for idea in self.ai_ideas:
            self.ai_ideas_output.append(f"{idea}\n{'-'*30}")

    def add_task(self):
        task, ok = QInputDialog.getText(self, "Добавить задачу/запрос", "Опишите задачу для AI:")
        if ok and task.strip():
            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
            self.tasks.append(entry)
            self.update_tasks_tab()

    def generate_ai_task(self):
        """
        Генерирует рекомендацию по доработке/задачу для AI на основе summary.
        """
        if not self.meta_summary_cache:
            self.show_meta_summary()
        prompt = (
            "Посмотри на summary файлов и сформулируй одну актуальную задачу для развития проекта — "
            "что можно улучшить или внедрить первым делом:"
            "\n\nСписок summary по файлам:\n"
        )
        text_summary = ""
        for rel_dir, files in (self.meta_summary_cache or {}).items():
            for f in files:
                summary = f['summary']
                summary_str = summary if isinstance(summary, str) else str(summary)
                text_summary += f"{f['name']}: {summary_str}\n"
        prompt += text_summary + "\n\nОтветь кратко, одна задача:"
        task = self.code_analyzer.chat(prompt, system_msg="Ты — AI-продукт менеджер.")
        entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
        self.tasks.append(entry)
        self.update_tasks_tab()
        QMessageBox.information(self, "AI-задача получена", f"AI-задача:\n{task.strip()}")

    def update_tasks_tab(self):
        self.tasks_output.clear()
        self.tasks_output.append("📝 <b>Список текущих задач и запросов для AI/пользователя:</b>\n")
        for task in self.tasks:
            self.tasks_output.append(f"{task}\n{'-'*30}")

    def update_history_tab(self):
        self.history_output.clear()
        self.history_output.append("🕓 <b>История изменений/логов процесса:</b>\n")
        for entry in self.history[-100:]:
            self.history_output.append(f"{entry}\n{'-'*30}")

class MainWindow(QMainWindow):
    """
    Главное окно Aideon 5.0: ChatPanel + расширенная SelfImproverPanel
    """
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}

        self.setGeometry(100, 100, 1400, 850)
        self.setMinimumSize(1100, 650)
        self.setWindowTitle("Aideon 5.0")

        self._create_menu_bar()
        self._init_ui()
        self.load_settings()

    def _create_menu_bar(self):
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        file_menu = menubar.addMenu("Файл")
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def _init_ui(self):
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.chat_panel = ChatPanel(config=self.config, parent=self)
        self.self_improver_panel = SelfImproverPanel(
            config=self.config,
            chat_panel=self.chat_panel,
            parent=self
        )

        splitter.addWidget(self.chat_panel)
        splitter.addWidget(self.self_improver_panel)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(splitter)
        self.setCentralWidget(central_widget)

    def load_settings(self):
        settings = QSettings("Aideon", "Aideon5.0")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
        window_state = settings.value("windowState")
        if window_state:
            self.restoreState(window_state)

    def save_settings(self):
        settings = QSettings("Aideon", "Aideon5.0")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        self.save_settings()
        super().closeEvent(event)