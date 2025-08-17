"""
Модуль для внесения исправлений в код (по запросу AI).
Автоматически тестирует код после исправления, логирует изменения и позволяет откатываться.
"""

import openai
import difflib
import os
import json
from app.utils import load_api_key
from app.core.file_manager import FileManager
from app.modules.runner import CodeRunner

class CodeFixer:
    def __init__(self, config):
        self.config = config or {}
        self.api_key = load_api_key(self.config)
        self.model = self.config.get("model_name", "gpt-4-turbo")
        self.file_manager = FileManager()
        self.runner = CodeRunner()
        self.history_path = "app/logs/history.json"  # Файл истории изменений

    def suggest_fixes(self, code_text, file_path=None):
        """
        Запрос к GPT, чтобы предложить исправления/рефакторинг кода.
        """
        openai.api_key = self.api_key

        # Получаем структуру проекта
        project_tree = self.file_manager.get_project_tree("app")

        # Формируем полный контекст
        prompt = (
            "Ты — Aideon, AI-ассистент по исправлению кода.\n"
            "Тебе дана структура проекта:\n\n"
            f"{project_tree}\n\n"
            "Теперь исправь следующий код:\n"
            f"{code_text}\n\n"
            "Ответ должен быть в JSON формате с ключами:\n"
            "{\n"
            "  \"chat\": \"...\",  // Ответ в чате\n"
            "  \"problems\": \"...\",  // Найденные проблемы\n"
            "  \"plan\": \"...\",  // Пошаговый план исправления\n"
            "  \"code\": \"...\",  // Исправленный код\n"
            "  \"diff\": \"...\"  // Разница между старым и новым кодом\n"
            "}\n"
            "Не добавляй ничего, кроме JSON."
        )

        try:
            response = openai.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": f"Исправь код в файле {file_path or 'без имени'}:\n{code_text}"}
                ],
                temperature=0.7
            )

            return response["choices"][0]["message"]["content"]

        except Exception as e:
            return f"Ошибка при обращении к AI: {e}"

    def apply_fixes(self, original_code, fixed_code, file_path):
        """
        Применяет исправления, записывая новый код в файл.
        """
        backup_path = f"{file_path}.backup"

        # Создаём бэкап перед изменением
        try:
            with open(file_path, "r", encoding="utf-8") as original, open(backup_path, "w", encoding="utf-8") as backup:
                backup.write(original.read())
        except Exception as e:
            return f"Ошибка при создании резервной копии: {e}"

        diff = self.generate_diff(original_code, fixed_code)

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(fixed_code)

            # Запускаем тест после исправления
            return self.run_tests(file_path, diff, fixed_code)

        except Exception as e:
            return f"Ошибка при записи исправленного кода: {e}"

    def generate_diff(self, original_code, fixed_code):
        """
        Генерирует diff между старым и новым кодом.
        """
        original_lines = original_code.splitlines(keepends=True)
        fixed_lines = fixed_code.splitlines(keepends=True)

        diff = difflib.unified_diff(original_lines, fixed_lines, lineterm="")
        return "\n".join(diff)

    def run_tests(self, file_path, diff, fixed_code):
        """
        Запускает тестирование кода после исправления.
        Если тесты не проходят, откатываемся к бэкапу и записываем это в историю.
        """
        file_name = os.path.basename(file_path)
        stdout, stderr, return_code = self.runner.run_code(file_name)

        history_entry = {
            "file": file_name,
            "diff": diff,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "status": "Успешно" if return_code == 0 else "Ошибка"
        }

        # Записываем историю исправлений
        self._save_to_history(history_entry)

        if return_code == 0:
            return f"Исправления успешно применены и протестированы:\n{diff}\nВывод тестов:\n{stdout}"
        else:
            # Откатываем изменения, если тесты не прошли
            backup_path = f"{file_path}.backup"
            if os.path.exists(backup_path):
                os.replace(backup_path, file_path)
                history_entry["status"] = "Откат к предыдущей версии"
                self._save_to_history(history_entry)
                return f"Ошибка во время тестирования! Код откатился к предыдущей версии.\n{stderr}"
            else:
                return f"Ошибка во время тестирования, но резервной копии нет!\n{stderr}"

    def _save_to_history(self, entry):
        """
        Сохраняет информацию об исправлении в history.json.
        """
        history = self._load_history()
        history.append(entry)

        with open(self.history_path, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=4, ensure_ascii=False)

    def _load_history(self):
        """
        Загружает историю исправлений.
        """
        if not os.path.exists(self.history_path):
            return []
        with open(self.history_path, "r", encoding="utf-8") as f:
            return json.load(f)