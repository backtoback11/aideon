from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextEdit

class PanelIssues(QWidget):
    def __init__(self, parent=None):
        """
        Панель проблем, найденных AI в коде.
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.label = QLabel("Найденные проблемы")
        layout.addWidget(self.label)

        self.issues_output = QTextEdit()
        self.issues_output.setReadOnly(True)
        layout.addWidget(self.issues_output)

        self.setLayout(layout)

    def setText(self, text: str):
        """
        Обновляет список найденных проблем.
        """
        self.issues_output.setText(text)