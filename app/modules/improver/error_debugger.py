import json
from typing import Optional
from app.logger import log_info, log_error


class ErrorDebugger:
    """
    Отвечает за диагностику и исправление ошибок после неудачного применения патча.
    Запрашивает у GPT исправленный код на основе сообщения об ошибке.
    """

    def __init__(self, chatgpt_client):
        self.chatgpt = chatgpt_client

    def build_prompt(self, file_path: str, original_code: str, error_message: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": (
                    "Ты — опытный Python-разработчик. "
                    "Твоя задача — исправить ошибки в коде на основе сообщения об ошибке, "
                    "не нарушая рабочую логику."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Путь к файлу: {file_path}\n\n"
                    f"Оригинальный код (после патча):\n{original_code}\n\n"
                    f"Ошибка выполнения:\n{error_message}\n\n"
                    "Проанализируй ошибку и предложи полную, исправленную версию кода."
                    " Ответ должен содержать только полный исправленный код файла."
                )
            }
        ]

    def request_fix(self, file_path: str, original_code: str, error_message: str) -> Optional[str]:
        try:
            messages = self.build_prompt(file_path, original_code, error_message)
            response = self.chatgpt.chat(messages)
            log_info(f"[ErrorDebugger] ✅ Получен исправленный код для {file_path}.")
            return response
        except Exception as e:
            log_error(f"[ErrorDebugger] ❌ Ошибка при запросе исправления: {e}")
            return None