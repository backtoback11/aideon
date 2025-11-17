# app/modules/fixer.py
"""
Модуль для внесения исправлений в код (по запросу AI).
Автоматически тестирует код после исправления, логирует изменения и позволяет откатываться.
Совместим с новым SDK OpenAI (>=1.x) и имеет фолбэк на старый.

Актуализации:
- Переведён на новый интерфейс CodePatcher (apply_patch_no_prompt без save_only/interactive_confirm).
- Добавлены безопасные вызовы агентских событий (emit_*), если доступны в app.logger.
"""

from __future__ import annotations

import difflib
import json
import os
from typing import Any, Dict, Optional

from app.core.file_manager import FileManager
from app.modules.runner import CodeRunner
from app.modules.improver.patcher import CodePatcher
from app.modules.utils import load_api_key, load_model_name, load_temperature
from app.logger import log_info, log_warning, log_error

# Опциональные агентские события (если в logger есть расширения — используем; иначе — no-op)
try:
    from app.logger import (
        set_agent_context,
        emit_event,
        emit_tool_call,
        emit_agent_error,
        emit_action,
    )
except Exception:  # мягкий фолбэк — никакого падения, просто пустые функции
    def set_agent_context(*args, **kwargs):  # type: ignore
        return None
    def emit_event(*args, **kwargs):  # type: ignore
        return None
    def emit_tool_call(*args, **kwargs):  # type: ignore
        return None
    def emit_agent_error(*args, **kwargs):  # type: ignore
        return None
    def emit_action(*args, **kwargs):  # type: ignore
        return None

# Новый SDK (openai>=1.x)
try:
    from openai import OpenAI
    _HAS_OAI_CLIENT = True
except Exception:
    _HAS_OAI_CLIENT = False

# Старый SDK (openai<1.x)
try:
    import openai  # type: ignore
except Exception:
    openai = None  # type: ignore


class CodeFixer:
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}

        # Конфиг/ENV
        self.api_key = load_api_key(self.config)
        self.model = load_model_name(self.config) or "gpt-4o"
        self.temperature = load_temperature(self.config)

        # Инструменты
        self.file_manager = FileManager()
        self.runner = CodeRunner()
        # единая точка бэкапа/диффа/записи (совместимо с актуальной версией)
        self.patcher = CodePatcher()

        # История
        self.history_path = os.path.join("app", "logs", "history.json")
        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)

        # OpenAI client (новый SDK)
        self._client: Optional["OpenAI"] = None
        if _HAS_OAI_CLIENT:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception as e:
                log_warning(f"[CodeFixer] Не удалось инициализировать OpenAI client: {e}")
                self._client = None

        # Агентский контекст (если включён в логгере)
        set_agent_context(
            agent_id=self.config.get("agent_id", "aideon-fixer"),
            run_id=self.config.get("run_id", None),
            task_id=self.config.get("task_id", None),
        )

        log_info(f"[CodeFixer] ✅ Инициализирован. Модель={self.model}, temp={self.temperature}")

    # ---------- GPT ----------

    def _chat(self, messages: list[dict[str, str]]) -> str:
        """
        Унифицированный вызов чата:
        - сначала пытаемся новый SDK (chat.completions),
        - затем — старый SDK (ChatCompletion).
        """
        # Новый SDK
        if self._client is not None:
            try:
                emit_action(step="fixer_chat", status="started", provider="openai", sdk=">=1.x")
                resp = self._client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
                out = (resp.choices[0].message.content or "").strip()
                emit_action(step="fixer_chat", status="done", chars=len(out))
                return out
            except Exception as e:
                # Если 401/invalid key — возвращаем понятное сообщение
                msg = str(e)
                if "401" in msg or "invalid_api_key" in msg or "Incorrect API key" in msg:
                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
                log_warning(f"[CodeFixer] Ошибка нового SDK: {e}")
                emit_agent_error("fixer_chat_newsdk_error", error=str(e))

        # Старый SDK
        if openai is not None:
            try:
                emit_action(step="fixer_chat", status="started", provider="openai", sdk="<1.x")
                openai.api_key = self.api_key
                resp = openai.ChatCompletion.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                )
                out = (resp["choices"][0]["message"]["content"] or "").strip()
                emit_action(step="fixer_chat", status="done", chars=len(out))
                return out
            except Exception as e2:
                msg = str(e2)
                if "401" in msg or "invalid_api_key" in msg or "Incorrect API key" in msg:
                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
                emit_agent_error("fixer_chat_oldsdk_error", error=str(e2))
                return f"Ошибка при обращении к AI: {e2}"

        return "Ошибка: OpenAI SDK не найден."

    # ---------- Публичные методы ----------

    def suggest_fixes(self, code_text: str, file_path: Optional[str] = None) -> str:
        """
        Запрос к GPT, чтобы предложить исправления/рефакторинг кода.
        Возвращает СЫРОЙ текст (ожидается JSON по протоколу подсказки).
        """
        project_tree = self.file_manager.get_project_tree("app")

        system_prompt = (
            "Ты — Aideon, AI-ассистент по исправлению кода.\n"
            "Тебе дана структура проекта (вырезка):\n\n"
            f"{project_tree}\n\n"
            "Работай строго по формату JSON:\n"
            "{\n"
            '  "chat": "...",\n'
            '  "problems": "...",\n'
            '  "plan": "...",\n'
            '  "code": "...",\n'
            '  "diff": "..." \n'
            "}\n"
            "Никакого текста вне JSON."
        )

        user_prompt = (
            f"Исправь код в файле {file_path or 'без имени'}:\n"
            f"{code_text}\n\n"
            "Верни строго JSON по указанной схеме."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_prompt},
        ]

        log_info("[CodeFixer] 🤖 Запрос AI на предложение исправлений…")
        emit_event("fixer_suggest_start", file=file_path or "unknown")
        result = self._chat(messages)
        emit_event("fixer_suggest_done", file=file_path or "unknown", length=len(result or ""))
        log_info(f"[CodeFixer] 📨 Ответ от AI получен ({len(result)} симв.)")
        return result

    def apply_fixes(self, original_code: str, fixed_code: str, file_path: str) -> str:
        """
        Применяет исправления:
        - бэкап/дифф/запись — через CodePatcher.apply_patch_no_prompt(...)
        - затем запускает тесты; при ошибке — откат бэкапа выполняется тут же вручную
        """
        try:
            # Новый актуальный интерфейс: создаём бэкап, сохраняем diff и перезаписываем файл
            self.patcher.apply_patch_no_prompt(
                file_path=file_path,
                old_code=original_code,
                new_code=fixed_code,
                save_backup=True,   # делаем бэкап
                save_diff=True,     # сохраняем diff
            )
            emit_tool_call("patcher", "apply_patch_no_prompt", file=file_path, mode="write")
            log_info(f"[CodeFixer] ✅ Патч применён: {file_path}")
        except Exception as e:
            log_error(f"[CodeFixer] ❌ Ошибка при применении патча: {e}")
            emit_agent_error("fixer_apply_patch_error", file=file_path, error=str(e))
            return f"Ошибка при записи исправленного кода: {e}"

        # Сгенерируем diff для отчёта (дополнительно к сохранённому в patches/)
        diff = self.generate_diff(original_code, fixed_code)

        # Запуск проверки/тестов
        return self.run_tests(file_path, diff, fixed_code)

    def generate_diff(self, original_code: str, fixed_code: str) -> str:
        """
        Генерирует unified diff между старым и новым кодом.
        """
        original_lines = original_code.splitlines(keepends=True)
        fixed_lines = fixed_code.splitlines(keepends=True)

        diff = difflib.unified_diff(
            original_lines, fixed_lines, fromfile="original", tofile="fixed", lineterm=""
        )
        return "\n".join(diff)

    def run_tests(self, file_path: str, diff: str, fixed_code: str) -> str:
        """
        Запускает выполнение файла после исправления.
        Если выполнение завершилось с ошибкой — пытается откатиться к бэкапу
        (бэкап делал CodePatcher перед записью).
        """
        file_name = os.path.basename(file_path)
        log_info(f"[CodeFixer] 🧪 Запуск проверки файла: {file_name}")
        emit_action(step="fixer_run", status="started", file=file_name)

        stdout, stderr, return_code = self.runner.run_code(file_name)

        history_entry = {
            "file": file_name,
            "diff": diff,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "status": "Успешно" if return_code == 0 else "Ошибка",
        }
        self._save_to_history(history_entry)

        if return_code == 0:
            emit_action(step="fixer_run", status="done", file=file_name, result="ok")
            log_info("[CodeFixer] ✅ Исправления применены и проверка прошла успешно")
            return f"Исправления успешно применены и протестированы:\n{diff}\nВывод:\n{stdout}"

        # Ошибка — попробуем откатиться (бэкап создавал патчер)
        log_warning("[CodeFixer] ❌ Ошибка при проверке — попытка отката к бэкапу")
        emit_action(step="fixer_run", status="done", file=file_name, result="error")

        backup_dir = self.patcher.backup_dir
        base = os.path.basename(file_path)
        try:
            cand = [
                f for f in os.listdir(backup_dir)
                if f.startswith(base + ".") and f.endswith(".bak")
            ]
            cand.sort(reverse=True)
            if cand:
                latest = os.path.join(backup_dir, cand[0])
                with open(latest, "r", encoding="utf-8") as bf, open(file_path, "w", encoding="utf-8") as wf:
                    wf.write(bf.read())
                history_entry["status"] = "Откат к предыдущей версии"
                self._save_to_history(history_entry)
                log_warning(f"[CodeFixer] ↩️ Откат выполнен из бэкапа: {latest}")
                emit_event("fixer_rollback_done", file=file_name, backup=latest)
                return f"Ошибка во время проверки! Код откатился к предыдущей версии.\n{stderr}"
            else:
                log_error("[CodeFixer] Бэкап не найден — откат невозможен")
                emit_agent_error("fixer_rollback_missing_backup", file=file_name)
                return f"Ошибка во время тестирования, и резервной копии не найдено!\n{stderr}"
        except Exception as e:
            log_error(f"[CodeFixer] Ошибка при откате: {e}")
            emit_agent_error("fixer_rollback_error", file=file_name, error=str(e))
            return f"Ошибка во время тестирования и при откате: {e}\n{stderr}"

    # ---------- История ----------

    def _save_to_history(self, entry: Dict[str, Any]) -> None:
        """
        Сохраняет информацию об исправлении в history.json (без падений на битом файле).
        """
        history = self._load_history()
        history.append(entry)
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log_warning(f"[CodeFixer] Не удалось записать историю: {e}")

    def _load_history(self) -> list[Dict[str, Any]]:
        """
        Загружает историю исправлений, возвращает [] при любой ошибке.
        """
        if not os.path.exists(self.history_path):
            return []
        try:
            with open(self.history_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception:
            return []