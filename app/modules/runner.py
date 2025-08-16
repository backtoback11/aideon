"""
Модуль для тестирования исправленного кода.
Поддерживает обычный запуск кода и запуск `pytest` для тестов.
"""

import subprocess
import os

class CodeRunner:
    def __init__(self, sandbox_path="app/sandbox"):
        """
        sandbox_path - путь к директории с тестируемыми файлами.
        """
        self.sandbox_path = sandbox_path
        os.makedirs(self.sandbox_path, exist_ok=True)

    def run_code(self, file_name):
        """
        Запускает код в песочнице и возвращает stdout/stderr.
        Если это тестовый файл, использует `pytest`.
        """
        abs_path = os.path.join(self.sandbox_path, file_name)
        if not os.path.exists(abs_path):
            return None, "Ошибка: файл не найден.", -1

        try:
            if file_name.startswith("test_") or "test" in file_name:
                # Если файл тестовый, используем pytest
                result = subprocess.run(
                    ["pytest", abs_path, "--tb=short", "--disable-warnings"],
                    capture_output=True,
                    text=True,
                    timeout=15
                )
            else:
                # Обычный запуск кода
                result = subprocess.run(
                    ["python", abs_path],
                    capture_output=True,
                    text=True,
                    timeout=10
                )

            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            return None, "Ошибка: превышено время ожидания выполнения.", -1

        except Exception as e:
            return None, f"Ошибка выполнения: {e}", -1

    def run_all_tests(self):
        """
        Запускает все тесты в `sandbox/`, если такие файлы есть.
        """
        try:
            result = subprocess.run(
                ["pytest", self.sandbox_path, "--tb=short", "--disable-warnings"],
                capture_output=True,
                text=True,
                timeout=30  # Даем больше времени для всех тестов
            )
            return result.stdout, result.stderr, result.returncode

        except subprocess.TimeoutExpired:
            return None, "Ошибка: превышено время ожидания выполнения.", -1

        except Exception as e:
            return None, f"Ошибка выполнения: {e}", -1