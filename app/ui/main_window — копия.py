# app/ui/main_window.py

import os
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QMenuBar, QLabel,
    QDockWidget, QScrollArea
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt, QSettings

# Импорт остальных панелей
from .panels.panel_issues import PanelIssues
from .panels.panel_solutions import PanelSolutions
from .panels.panel_process import PanelProcess
from .panels.panel_result import PanelResult
from .panels.panel_history import PanelHistory  # Новая панель для истории

from .chat_panel import ChatPanel


class MainWindow(QMainWindow):
    """
    Главное окно приложения Aideon 5.0.  
    Содержит меню, центральный ChatPanel и док-панели:
      - PanelIssues (проблемы/ошибки),
      - PanelSolutions (план/правки),
      - PanelProcess (логи процесса),
      - PanelResult (итоговый результат),
      - PanelHistory (история изменений).
    """
    def __init__(self, config=None):
        super().__init__()
        self.config = config or {}

        # Устанавливаем начальный и минимальный размеры окна
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)
        self.setWindowTitle("Aideon 5.0")

        # Инициализируем основные панели
        self.panel_issues = PanelIssues()
        self.panel_solutions = PanelSolutions()
        self.panel_process = PanelProcess()
        self.panel_result = PanelResult()
        self.panel_history = PanelHistory()  # Новая панель для истории

        # Dock-панели (изначально None)
        self.issues_dock = None
        self.solutions_dock = None
        self.process_dock = None
        self.result_dock = None
        self.history_dock = None  # Dock-панель для истории

        # Создаём меню и основной UI
        self._create_menu_bar()
        self._init_ui()

        # Восстанавливаем состояние окон (QSettings)
        self.load_settings()

        # Автоматически открываем все панели при запуске
        self.show_issues_panel()
        self.show_solutions_panel()
        self.show_process_panel()
        self.show_result_panel()
        self.show_history_panel()

    def _create_menu_bar(self):
        """Создание главного меню в верхней части окна."""
        menubar = QMenuBar(self)
        self.setMenuBar(menubar)

        # Меню "Файл"
        file_menu = menubar.addMenu("Файл")
        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню "Панели"
        panels_menu = menubar.addMenu("Панели")

        issues_action = QAction("Открыть Проблемы", self)
        issues_action.triggered.connect(self.show_issues_panel)
        panels_menu.addAction(issues_action)

        solutions_action = QAction("Открыть План/Правки", self)
        solutions_action.triggered.connect(self.show_solutions_panel)
        panels_menu.addAction(solutions_action)

        process_action = QAction("Открыть Процесс", self)
        process_action.triggered.connect(self.show_process_panel)
        panels_menu.addAction(process_action)

        result_action = QAction("Открыть Результат", self)
        result_action.triggered.connect(self.show_result_panel)
        panels_menu.addAction(result_action)

        # Пункт меню для "Истории"
        history_action = QAction("Открыть Историю", self)
        history_action.triggered.connect(self.show_history_panel)
        panels_menu.addAction(history_action)

    def _init_ui(self):
        """
        Создаём центральный виджет (ChatPanel), где вся основная логика:
        - Отправка запросов к ChatGPT / StarCoder
        - Автоанализ проекта
        - Генерация кода StarCoder
        и т. д.
        """
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)

        self.chat_panel = ChatPanel(
            config=self.config,
            panel_issues=self.panel_issues,
            panel_solutions=self.panel_solutions,
            panel_process=self.panel_process,
            panel_result=self.panel_result,
            parent=self
        )
        layout.addWidget(self.chat_panel)

        self.setCentralWidget(central_widget)

    # ----------------------------------------------------------------
    #  Создание QDockWidget со скроллом
    # ----------------------------------------------------------------
    def _make_scrolled_dock(self, title, panel):
        """
        Оборачивает panel (QWidget) в QScrollArea для прокрутки,
        а затем вставляет в QDockWidget. Возвращает готовый QDockWidget.
        """
        dock = QDockWidget(title, self)
        scroll = QScrollArea()
        scroll.setWidget(panel)
        scroll.setWidgetResizable(True)
        dock.setWidget(scroll)

        # Разрешаем стыковать панель со всех сторон
        dock.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea
            | Qt.DockWidgetArea.RightDockWidgetArea
            | Qt.DockWidgetArea.TopDockWidgetArea
            | Qt.DockWidgetArea.BottomDockWidgetArea
        )
        return dock

    # ----------------------------------------------------------------
    # Методы показа/скрытия док-панелей
    # ----------------------------------------------------------------
    def show_issues_panel(self):
        """Открывает панель 'Проблемы'."""
        if not self.issues_dock:
            self.issues_dock = self._make_scrolled_dock(
                "Проблемы / Описание задачи", self.panel_issues
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.issues_dock)
            self.issues_dock.closeEvent = lambda event: self._clear_dock("issues")

        if not self.issues_dock.isVisible():
            self.issues_dock.show()

    def show_solutions_panel(self):
        """Открывает панель 'План/Правки'."""
        if not self.solutions_dock:
            self.solutions_dock = self._make_scrolled_dock(
                "Предложенные правки / План действий", self.panel_solutions
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.solutions_dock)
            self.solutions_dock.closeEvent = lambda event: self._clear_dock("solutions")

        if not self.solutions_dock.isVisible():
            self.solutions_dock.show()

    def show_process_panel(self):
        """Открывает панель 'Процесс'."""
        if not self.process_dock:
            self.process_dock = self._make_scrolled_dock(
                "Текущий процесс / Логи", self.panel_process
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.process_dock)
            self.process_dock.closeEvent = lambda event: self._clear_dock("process")

        if not self.process_dock.isVisible():
            self.process_dock.show()

    def show_result_panel(self):
        """Открывает панель 'Результат'."""
        if not self.result_dock:
            self.result_dock = self._make_scrolled_dock(
                "Итоговый результат / Визуализация", self.panel_result
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.result_dock)
            self.result_dock.closeEvent = lambda event: self._clear_dock("result")

        if not self.result_dock.isVisible():
            self.result_dock.show()

    def show_history_panel(self):
        """Открывает панель 'История' (panel_history)."""
        if not self.history_dock:
            from .panels.panel_history import PanelHistory
            if not hasattr(self, 'panel_history'):
                self.panel_history = PanelHistory()

            self.history_dock = self._make_scrolled_dock(
                "История исправлений", self.panel_history
            )
            self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.history_dock)
            self.history_dock.closeEvent = lambda event: self._clear_dock("history")

        if not self.history_dock.isVisible():
            self.history_dock.show()

    def _clear_dock(self, panel_name):
        """
        Очищает DockWidget при закрытии окна панели (чтобы при повторном открытии
        создавался новый экземпляр).
        """
        if panel_name == "issues" and self.issues_dock:
            self.issues_dock.deleteLater()
            self.issues_dock = None
        elif panel_name == "solutions" and self.solutions_dock:
            self.solutions_dock.deleteLater()
            self.solutions_dock = None
        elif panel_name == "process" and self.process_dock:
            self.process_dock.deleteLater()
            self.process_dock = None
        elif panel_name == "result" and self.result_dock:
            self.result_dock.deleteLater()
            self.result_dock = None
        elif panel_name == "history" and self.history_dock:
            self.history_dock.deleteLater()
            self.history_dock = None

    # ----------------------------------------------------------------
    # Сохранение/восстановление состояния окна
    # ----------------------------------------------------------------
    def load_settings(self):
        """Восстанавливает расположение/размеры окна, а также состояние док-панелей."""
        settings = QSettings("Aideon", "Aideon5.0")
        geometry = settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)

        windowState = settings.value("windowState")
        if windowState:
            self.restoreState(windowState)

    def save_settings(self):
        """Сохраняет расположение и состояние окон при выходе."""
        settings = QSettings("Aideon", "Aideon5.0")
        settings.setValue("geometry", self.saveGeometry())
        settings.setValue("windowState", self.saveState())

    def closeEvent(self, event):
        """При закрытии окна записываем настройки, чтобы восстановить их при следующем запуске."""
        self.save_settings()
        super().closeEvent(event)