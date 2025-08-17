from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit, QPushButton, QFileDialog, QMessageBox

class PanelResult(QWidget):
    def __init__(self, parent=None):
        """
        Панель итогового результата (исправленный код).
        """
        super().__init__(parent)
        self.current_code = None  # Хранит исправленный код
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Итоговый результат / Визуализация")
        layout.addWidget(self.label)

        # Поле для отображения исправленного кода
        self.result_output = QTextEdit()
        self.result_output.setReadOnly(True)
        layout.addWidget(self.result_output)

        # Кнопка для сохранения исправленного кода
        self.save_button = QPushButton("Сохранить исправленный код")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_code)
        layout.addWidget(self.save_button)

        self.setLayout(layout)

    def setText(self, text: str):
        """
        Обновляет отображаемый результат и активирует кнопку сохранения.
        """
        self.current_code = text
        self.result_output.setText(text)
        self.save_button.setEnabled(bool(text))  # Активируем кнопку, если есть код

    def save_code(self):
        """
        Открывает диалог сохранения и записывает исправленный код в файл.
        """
        if not self.current_code:
            QMessageBox.warning(self, "Ошибка", "Нет исправленного кода для сохранения.")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "Сохранить исправленный код", "", "Python Files (*.py);;Все файлы (*)")

        if file_path:
            try:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(self.current_code)
                QMessageBox.information(self, "Сохранение завершено", f"Исправленный код сохранён в {file_path}")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Ошибка при сохранении файла: {e}")