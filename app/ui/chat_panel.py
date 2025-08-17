import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel
)
from PyQt6.QtCore import Qt

from app.modules.analyzer import CodeAnalyzer

class ChatPanel(QWidget):
    """
    Минимальная панель чата Aideon 5.0 — чат с ИИ.
    Показывает ручные сообщения и все автоматические GPT-запросы/ответы системы.
    """

    def __init__(self, config=None, parent=None):
        super().__init__(parent)

        self.config = config or {}
        self.analyzer = CodeAnalyzer(self.config)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        # Заголовок
        layout.addWidget(QLabel("Aideon: Чат с ИИ (ручной и системный)"))

        # Чат-лог
        self.chat_log = QTextEdit()
        self.chat_log.setReadOnly(True)
        self.chat_log.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        self.chat_log.setStyleSheet("background-color: #f4f4f4; padding: 5px;")
        layout.addWidget(self.chat_log)

        # Ввод + кнопка отправки
        self.input_text = QTextEdit()
        self.input_text.setFixedHeight(50)

        self.send_chat_button = QPushButton("Отправить")
        self.send_chat_button.clicked.connect(self.handle_send_chat_gpt)

        row_top = QHBoxLayout()
        row_top.addWidget(self.input_text)
        row_top.addWidget(self.send_chat_button)
        layout.addLayout(row_top)

        self.setLayout(layout)

    def handle_send_chat_gpt(self):
        """Отправляет user_text напрямую в ChatGPT, выводит промт и ответ."""
        import openai

        user_text = self.input_text.toPlainText().strip()
        if not user_text:
            return
        self.input_text.clear()

        # 1. Пользовательское сообщение
        self.add_user_message(user_text)

        # 2. Сформировать промт messages
        prompt = [
            {"role": "system", "content": "Ты — Aideon, самообучающийся AI-ассистент."},
            {"role": "user", "content": user_text}
        ]

        # 3. Вывести запрос в чат
        self.add_gpt_request(prompt)

        # 4. Отправить в OpenAI
        openai.api_key = self.analyzer.api_key
        try:
            response = openai.ChatCompletion.create(
                model=self.analyzer.openai_model,
                messages=prompt,
                temperature=self.analyzer.temperature
            )
            gpt_answer = response["choices"][0]["message"]["content"]
            self.add_gpt_response(gpt_answer)
        except Exception as e:
            self._log_chat(f"<b>Ошибка чата:</b> {e}")

    # ===== Методы для вывода GPT-запросов и ответов из других модулей =====

    def add_gpt_request(self, prompt):
        """Вывести промт (messages) к GPT — список или строкой."""
        if isinstance(prompt, list):
            pretty = json.dumps(prompt, ensure_ascii=False, indent=2)
        else:
            pretty = str(prompt)
        self._log_chat(f"<span style='color: #555'>→ <b>Запрос к GPT:</b></span><br><pre>{pretty}</pre>")

    def add_gpt_response(self, answer):
        """Вывести ответ от GPT (dict или строка)."""
        if isinstance(answer, dict):
            pretty = json.dumps(answer, ensure_ascii=False, indent=2)
        else:
            pretty = str(answer)
        self._log_chat(f"<span style='color: #285b2a'>← <b>Ответ GPT:</b></span><br><pre>{pretty}</pre>")

    def add_user_message(self, msg):
        """Вывести пользовательское сообщение (ручной ввод)."""
        self._log_chat(f"<b>Вы:</b> {msg}")

    def _log_chat(self, msg: str):
        self.chat_log.append(msg)
        self.chat_log.verticalScrollBar().setValue(
            self.chat_log.verticalScrollBar().maximum()
        )