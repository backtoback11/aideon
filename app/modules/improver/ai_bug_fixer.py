# app/modules/improver/ai_bug_fixer.py
from __future__ import annotations

from typing import Optional, Any, Callable
import time

from app.modules.analyzer import CodeAnalyzer
from app.logger import log_info, log_warning, log_error

# Опциональные агентские события (если расширения есть в logger — используем; иначе no-op)
try:
    from app.logger import (
        emit_event,
        emit_action,
        emit_agent_error,
    )
except Exception:
    def emit_event(*args, **kwargs):  # type: ignore
        return None
    def emit_action(*args, **kwargs):  # type: ignore
        return None
    def emit_agent_error(*args, **kwargs):  # type: ignore
        return None


def _strip_fences(text: str) -> str:
    """
    Убирает возможные ограждения кодом вида:
    ```python ... ``` или ``` ... ```
    без разрушения содержимого.
    """
    if not text:
        return text
    s = text.strip()
    if s.startswith("```"):
        # удалим начальный ```
        s = s[3:].lstrip()
        # если сразу идёт идентификатор языка — отрежем его до конца строки
        nl = s.find("\n")
        if nl != -1:
            s = s[nl + 1 :]
        else:
            # строка вида "```python" без переноса — возвращаем пусто
            return ""
        # убрать возможный завершающий ```
        if s.endswith("```"):
            s = s[: -3].rstrip()
    return s


class AIBugFixer:
    """
    Мини-модуль «AI-Assisted Bug Fixer».

    Задачи:
      1) На основе summary + кода попросить у GPT выявить вероятные баги и дать краткий план фикса.
      2) Запросить у GPT «новую версию файла» (полный текст), вернуть как строку без Markdown-ограждений.
      3) При ошибке применения — сделать до N повторов (итеративный цикл).

    Модуль НЕ работает с файловой системой напрямую — все действия записи выполняются внешними колбэками.
    """

    def __init__(self, analyzer: CodeAnalyzer, max_fix_cycles: int = 2):
        self.analyzer = analyzer
        self.max_fix_cycles = int(max_fix_cycles)

    # ---------- Промпты ----------

    def propose_fixes(self, file_path: str, summary: Any, code: str) -> str:
        """
        Просим у модели кратко описать потенциальные ошибки и план исправления (3–7 пунктов).
        Возвращает человекочитаемый текст (для логов/истории).
        """
        system_msg = "Ты — строгий и практичный ревьюер кода. Отвечай кратко и по делу."
        user_prompt = (
            "Тебе дан файл и его summary.\n\n"
            f"Файл: {file_path}\n"
            f"Summary:\n{summary}\n\n"
            "Код:\n"
            f"{code}\n\n"
            "Определи вероятные ошибки, точки риска и дай краткий план исправления "
            "(маркдаун-список, 3–7 пунктов). Если критичных ошибок нет, напиши 'Нет явных ошибок'."
        )
        try:
            emit_action(step="bugfixer_plan", status="started", file=file_path)
            plan = self.analyzer.chat(user_prompt, system_msg=system_msg)
            plan = (plan or "").strip() or "Нет ответа от модели"
            emit_action(step="bugfixer_plan", status="done", file=file_path, chars=len(plan))
            return plan
        except Exception as e:
            log_warning(f"[BugFixer] Не удалось получить план фиксов: {e}")
            emit_agent_error("bugfixer_plan_error", file=file_path, error=str(e))
            return f"Ошибка: {e}"

    def generate_fixed_code(self, file_path: str, summary: Any, code: str) -> Optional[str]:
        """
        Просим у модели вернуть ПОЛНУЮ обновлённую версию файла (единым текстом),
        без Markdown-разметки и комментариев вне кода.
        """
        system_msg = "Ты — опытный Python-разработчик. Верни только код файла, без Markdown."
        user_prompt = (
            "Верни ПОЛНУЮ обновлённую версию файла (единым текстом), исправив ошибки и повысив устойчивость.\n"
            "Не добавляй подсветку/форматирование/разметку — только чистый код.\n\n"
            f"Файл: {file_path}\n"
            f"Summary:\n{summary}\n\n"
            "Текущая версия:\n"
            f"{code}\n\n"
            "Требования:\n"
            "- Сохрани публичные API и совместимость с текущей логикой.\n"
            "- Не ломай зависимости проекта.\n"
            "- При сомнениях оставь краткий TODO-комментарий в коде.\n"
        )
        try:
            emit_action(step="bugfixer_generate", status="started", file=file_path)
            new_code = self.analyzer.chat(user_prompt, system_msg=system_msg)
            if not new_code:
                emit_action(step="bugfixer_generate", status="done", file=file_path, result="empty")
                return None
            stripped = _strip_fences(new_code)
            emit_action(step="bugfixer_generate", status="done", file=file_path, chars=len(stripped))
            return stripped
        except Exception as e:
            log_error(f"[BugFixer] Ошибка при запросе фикса: {e}")
            emit_agent_error("bugfixer_generate_error", file=file_path, error=str(e))
            return None

    # ---------- Итеративный цикл ----------

    def iterative_fix_cycle(
        self,
        file_path: str,
        summary: Any,
        old_code: str,
        apply_callback: Callable[[str], None],   # обязан применить патч/сохранить diff/и т.п. (может бросить исключение)
        on_error_callback: Callable[[Exception, int], None],  # уведомление о фейле применения
    ) -> Optional[str]:
        """
        Делает до N попыток получить и применить исправленный код.
        Возвращает применённый код (str) на успехе или None на неудаче.
        """
        for attempt in range(1, self.max_fix_cycles + 1):
            emit_event("bugfixer_attempt", file=file_path, attempt=attempt, total=self.max_fix_cycles)

            plan = self.propose_fixes(file_path, summary, old_code)
            log_info(f"[BugFixer] План фиксов (попытка {attempt}/{self.max_fix_cycles}):\n{plan}")

            new_code = self.generate_fixed_code(file_path, summary, old_code)
            if not new_code:
                log_warning("[BugFixer] Модель не вернула новую версию кода.")
                on_error_callback(RuntimeError("Модель не вернула код"), attempt)
                time.sleep(1.0 * attempt)
                continue

            try:
                apply_callback(new_code)  # внешний код решает: применить или только diff
                return new_code
            except Exception as e:
                on_error_callback(e, attempt)
                emit_agent_error("bugfixer_apply_error", file=file_path, error=str(e), attempt=attempt)
                # Небольшая экспоненциальная пауза между попытками
                time.sleep(1.0 * attempt)

        return None