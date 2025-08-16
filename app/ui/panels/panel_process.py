import os
import json
import signal
import subprocess

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTextEdit,
    QPushButton, QMessageBox, QHBoxLayout
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt, QTimer

from app.modules.runner import CodeRunner
from app.core.file_manager import FileManager
from app.modules.fixer import CodeFixer

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


class TestThread(QThread):
    """
    Поток, который запускает код в subprocess.Popen и
    построчно читает stdout/stderr, отправляя их наверх.
    """
    log_line = pyqtSignal(str)
    finished_signal = pyqtSignal(int)  # передаём returncode в конец
    error_signal = pyqtSignal(str)

    def __init__(self, file_path, sandbox_path="app/sandbox", parent=None):
        super().__init__(parent)
        self.file_path = file_path
        self.sandbox_path = sandbox_path
        self.process = None
        self.stop_requested = False

    def run(self):
        """
        Запускаем тест кода через Popen, читаем вывод построчно.
        Если пользователь попросит остановить — прерываем процесс.
        """
        abs_path = os.path.join(self.sandbox_path, self.file_path)
        if not os.path.exists(abs_path):
            self.error_signal.emit(f"Ошибка: файл не найден {self.file_path}")
            self.finished_signal.emit(-1)
            return

        try:
            # Запускаем Popen
            self.process = subprocess.Popen(
                ["python", abs_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                universal_newlines=True
            )

            # Построчно читаем stdout
            while True:
                if self.stop_requested:
                    # Если пользователь нажал "Остановить"
                    self.process.terminate()
                    self.finished_signal.emit(-1)
                    return

                line = self.process.stdout.readline()
                if not line:  # process stdout EOF
                    break
                self.log_line.emit(line.rstrip("\n"))

            # Читать оставшийся stderr
            err_data = self.process.stderr.read()
            if err_data:
                for line in err_data.splitlines():
                    self.log_line.emit(f"[stderr] {line}")

            retcode = self.process.wait()
            self.finished_signal.emit(retcode)

        except Exception as e:
            self.error_signal.emit(f"Ошибка выполнения: {e}")
            self.finished_signal.emit(-1)

    def stop(self):
        """Попросить поток прервать выполнение."""
        self.stop_requested = True
        if self.process:
            self.process.terminate()


class PanelProcess(QWidget):
    def __init__(self, config=None, parent=None):
        """
        Панель процесса выполнения кода и тестирования (с потоками).
        Добавляем визуализацию ресурсов (если psutil установлен).
        """
        super().__init__(parent)
        self.config = config or {}
        self.runner = CodeRunner()
        self.file_manager = FileManager()
        self.fixer = CodeFixer(self.config)
        self.current_file = None  # Файл для тестирования
        self.original_code = None  # Исходный код для возможного отката
        self.history_path = "app/logs/history.json"  # Путь к истории

        self.test_thread = None  # Будем хранить поток здесь

        # Логика ограничения длины лога
        self.max_log_lines = 1000

        self._init_ui()

        # Таймер для обновления статистики ресурсов (CPU/RAM)
        self.resource_timer = QTimer(self)
        self.resource_timer.setInterval(2000)  # обновлять раз в 2 сек
        self.resource_timer.timeout.connect(self._update_resource_stats)
        self.resource_timer.start()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Текущий процесс / Логи генерации")
        layout.addWidget(self.label)

        # Поле вывода логов
        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        # Разрешаем выделять и копировать текст
        self.log_output.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse 
            | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        layout.addWidget(self.log_output)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        self.run_button = QPushButton("Запустить тест")
        self.run_button.setEnabled(False)
        self.run_button.clicked.connect(self.run_test)
        btn_layout.addWidget(self.run_button)

        self.stop_button = QPushButton("Остановить тест")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_test)
        btn_layout.addWidget(self.stop_button)

        self.rollback_button = QPushButton("Откатить изменения")
        self.rollback_button.setEnabled(False)
        self.rollback_button.clicked.connect(self.rollback_changes)
        btn_layout.addWidget(self.rollback_button)

        self.clear_logs_button = QPushButton("Очистить логи")
        self.clear_logs_button.clicked.connect(self.clear_logs)
        btn_layout.addWidget(self.clear_logs_button)

        layout.addLayout(btn_layout)

        # Метка для отображения статистики ресурсов
        self.resource_label = QLabel("Статистика ресурсов: -")
        layout.addWidget(self.resource_label)

        self.setLayout(layout)

    def setText(self, text: str, file_path=None, original_code=None):
        """
        Обновляет метку self.label (описание),
        а также сохраняет путь к файлу для тестирования и оригинальный код (на случай отката).
        """
        self.label.setText(text)
        self.current_file = file_path
        self.original_code = original_code

        # Активируем кнопку запуска теста, если файл указан
        if file_path:
            self.run_button.setEnabled(True)
        else:
            self.run_button.setEnabled(False)

    # ----------------------------------------------------------------
    # Запуск теста (через QThread + Popen)
    # ----------------------------------------------------------------
    def run_test(self):
        """
        Запускает тестирование исправленного кода в отдельном потоке.
        """
        if not self.current_file:
            QMessageBox.warning(self, "Ошибка", "Нет файла для тестирования.")
            return

        file_name = os.path.basename(self.current_file)
        self._append_log(f"<b>Запуск теста для {file_name}...</b>")

        self.test_thread = TestThread(file_name, "app/sandbox")
        self.test_thread.log_line.connect(self.append_log_line)
        self.test_thread.finished_signal.connect(self.on_test_finished)
        self.test_thread.error_signal.connect(self.on_test_error)

        self.stop_button.setEnabled(True)
        self.rollback_button.setEnabled(False)
        self.run_button.setEnabled(False)

        self.test_thread.start()

    def stop_test(self):
        """
        Останавливает тест (terminate process).
        """
        if self.test_thread:
            self.test_thread.stop()
            self.stop_button.setEnabled(False)
            self._append_log("<b>Пользователь остановил тест.</b>")

    def append_log_line(self, line: str):
        """
        Добавляет в лог каждую строку stdout/stderr в реальном времени.
        """
        # Проверим, stderr ли
        if line.startswith("[stderr]"):
            # Красным цветом
            self._append_log(f'<span style="color:red;">{line}</span>')
        else:
            # Зеленым
            self._append_log(f'<span style="color:green;">{line}</span>')

    def on_test_finished(self, return_code: int):
        """
        Когда поток завершил работу (процесс закончился).
        """
        self.stop_button.setEnabled(False)
        self.run_button.setEnabled(True)
        if return_code == 0:
            QMessageBox.information(self, "Тест выполнен", "Код успешно выполнен без ошибок!")
            self.rollback_button.setEnabled(False)
        else:
            QMessageBox.critical(self, "Ошибка в коде",
                                 f"Во время выполнения кода возникли ошибки. (returncode={return_code})")
            self.rollback_button.setEnabled(True)

        self._save_test_history(return_code)

    def on_test_error(self, error_text: str):
        """
        Если в процессе выполнения произошла ошибка (файл не найден и т.д.).
        """
        self._append_log(f'<span style="color:red;">{error_text}</span>')

    # ----------------------------------------------------------------
    # Откат изменений
    # ----------------------------------------------------------------
    def rollback_changes(self):
        """
        Откатывает изменения в коде, если тесты не прошли.
        """
        if not self.current_file or not self.original_code:
            QMessageBox.warning(self, "Ошибка", "Нет данных для отката.")
            return

        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.original_code)

            self._append_log(f'<b>Код откатился к предыдущей версии:</b> {self.current_file}')
            QMessageBox.information(self, "Откат выполнен",
                                    "Файл восстановлен до исходного состояния.")
            self.rollback_button.setEnabled(False)

            # Логируем откат в историю
            self._save_rollback_history()

        except Exception as e:
            QMessageBox.critical(self, "Ошибка отката", f"Ошибка при восстановлении файла: {e}")

    # ----------------------------------------------------------------
    # Очистка логов
    # ----------------------------------------------------------------
    def clear_logs(self):
        """
        Очищает логи выполнения.
        """
        self.log_output.clear()

    # ----------------------------------------------------------------
    # Логирование в history
    # ----------------------------------------------------------------
    def _save_test_history(self, return_code: int):
        """
        Сохраняем итог теста (return_code) в history.json.
        """
        entry = {
            "action": "test_run",
            "file": self.current_file,
            "return_code": return_code,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._append_history(entry)

    def _save_rollback_history(self):
        """
        Сохраняет запись об откате.
        """
        entry = {
            "action": "rollback",
            "file": self.current_file,
            "time": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        self._append_history(entry)

    def _append_history(self, entry: dict):
        """
        Универсальный метод для записи в history.
        """
        history = self._load_history()
        history.append(entry)
        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def _load_history(self):
        """
        Загружает историю тестирования/действий из history.json.
        """
        if not os.path.exists(self.history_path):
            return []
        with open(self.history_path, "r", encoding="utf-8") as f:
            return json.load(f)

    # ----------------------------------------------------------------
    # Вспомогательные методы
    # ----------------------------------------------------------------

    def _append_log(self, text_html: str):
        """
        Добавляет строку в log_output с ограничением max_log_lines.
        """
        self.log_output.append(text_html)

        # Ограничиваем количество строк
        if self.log_output.document().blockCount() > self.max_log_lines:
            cursor = self.log_output.textCursor()
            cursor.movePosition(cursor.Start)
            cursor.select(cursor.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()

    def _update_resource_stats(self):
        """
        Обновляет self.resource_label,
        если psutil установлен, показываем usage memory / CPU.
        """
        if not PSUTIL_AVAILABLE:
            self.resource_label.setText("Статистика ресурсов: psutil не установлен")
            return

        # Использование CPU в %
        cpu_percent = psutil.cpu_percent(interval=None)
        # Использование памяти
        mem_info = psutil.virtual_memory()
        used_mb = int(mem_info.used / (1024 * 1024))

        self.resource_label.setText(
            f"Статистика ресурсов: CPU {cpu_percent:.1f}% | RAM used ~ {used_mb} MB"
        )