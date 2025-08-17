from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox, QTextEdit
from app.modules.fixer import CodeFixer
from app.core.file_manager import FileManager

class PanelSolutions(QWidget):
    def __init__(self, config=None, panel_process=None, parent=None):
        """
        Панель предложенных исправлений.
        """
        super().__init__(parent)
        self.config = config or {}
        self.fixer = CodeFixer(self.config)
        self.file_manager = FileManager()
        self.panel_process = panel_process  # Ссылка на панель процессов
        self.current_file = None  # Файл, в который будет применено исправление
        self.current_fixed_code = None  # Исправленный код от AI
        self.original_code = None  # Исходный код (для отката)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Предложенные правки / План действий")
        layout.addWidget(self.label)

        # Поле для просмотра `diff`
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        layout.addWidget(self.diff_view)

        # Кнопка для просмотра `diff`
        self.show_diff_button = QPushButton("Показать разницу (diff)")
        self.show_diff_button.setEnabled(False)
        self.show_diff_button.clicked.connect(self.show_diff)
        layout.addWidget(self.show_diff_button)

        # Кнопка для применения исправлений
        self.apply_button = QPushButton("Применить исправления")
        self.apply_button.setEnabled(False)
        self.apply_button.clicked.connect(self.apply_fixes)
        layout.addWidget(self.apply_button)

        # Кнопка для отката изменений
        self.rollback_button = QPushButton("Откатить исправления")
        self.rollback_button.setEnabled(False)
        self.rollback_button.clicked.connect(self.rollback_changes)
        layout.addWidget(self.rollback_button)

        self.setLayout(layout)

    def setText(self, text: str, file_path=None, fixed_code=None, original_code=None):
        """
        Обновляет текст, отображаемый на панели.
        Сохраняет путь к файлу, исправленный и оригинальный код.
        """
        self.label.setText(text)
        self.current_file = file_path
        self.current_fixed_code = fixed_code
        self.original_code = original_code

        # Если есть исправленный код и файл, активируем кнопки
        if fixed_code and file_path:
            self.apply_button.setEnabled(True)
            self.show_diff_button.setEnabled(True)

    def show_diff(self):
        """
        Показывает `diff` между оригинальным и исправленным кодом.
        """
        if not self.original_code or not self.current_fixed_code:
            QMessageBox.warning(self, "Ошибка", "Нет данных для сравнения `diff`.")
            return

        diff_result = self.fixer.generate_diff(self.original_code, self.current_fixed_code)
        self.diff_view.setText(f"<b>Разница между кодами:</b>\n\n{diff_result}")

    def apply_fixes(self):
        """
        Применяет исправления к файлу, записывая новый код.
        """
        if not self.current_file or not self.current_fixed_code:
            QMessageBox.warning(self, "Ошибка", "Нет доступного исправленного кода для применения.")
            return

        # Читаем исходный код перед заменой
        original_code = self.file_manager.read_file(self.current_file)
        if not original_code:
            QMessageBox.critical(self, "Ошибка", f"Не удалось прочитать файл: {self.current_file}")
            return

        # Применяем исправления через `fixer.py`
        result_message = self.fixer.apply_fixes(original_code, self.current_fixed_code, self.current_file)

        # Выводим результат в диалоговом окне
        QMessageBox.information(self, "Исправления применены", result_message)

        # Деактивируем кнопку после применения
        self.apply_button.setEnabled(False)
        self.rollback_button.setEnabled(True)  # Разрешаем откат изменений

        # Логируем в `panel_process`
        if self.panel_process:
            self.panel_process.log_output.append(f"<b>Исправления применены к файлу:</b> {self.current_file}")

    def rollback_changes(self):
        """
        Откатывает изменения, если тесты не прошли или пользователь передумал.
        """
        if not self.current_file or not self.original_code:
            QMessageBox.warning(self, "Ошибка", "Нет данных для отката.")
            return

        try:
            with open(self.current_file, "w", encoding="utf-8") as f:
                f.write(self.original_code)
            
            QMessageBox.information(self, "Откат выполнен", "Файл восстановлен до исходного состояния.")
            self.rollback_button.setEnabled(False)
            self.apply_button.setEnabled(True)  # Можно снова применить исправления

            # Логируем в `panel_process`
            if self.panel_process:
                self.panel_process.log_output.append(f"<b>Код откатился к предыдущей версии:</b> {self.current_file}")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка отката", f"Ошибка при восстановлении файла: {e}")