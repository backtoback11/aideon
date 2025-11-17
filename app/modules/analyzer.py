# app/modules/analyzer.py
from __future__ import annotations

import json
import time
from typing import Optional, List, Dict, Any

from app.core.file_manager import FileManager
from app.modules.utils import load_api_key, load_model_name, load_temperature

# Новый SDK (openai>=1.x)
try:
    from openai import OpenAI
    _HAS_OAI_CLIENT = True
except Exception:
    _HAS_OAI_CLIENT = False

# Старый SDK (openai<1.x) — совместимость
try:
    import openai  # type: ignore
except Exception:
    openai = None  # type: ignore


class CodeAnalyzer:
    """
    Анализ и генерация кода через OpenAI.
    - Ключ берём через load_api_key
    - Имя модели: ENV > config > "gpt-4o"
    - Поддержка нового и старого SDK
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.file_manager = FileManager()

        self.api_key = load_api_key(self.config)
        self.openai_model = load_model_name(self.config) or "gpt-4o"
        self.temperature = load_temperature(self.config)
        self.max_context_tokens = int(self.config.get("max_context_tokens", 8192))
        self.request_timeout = int(self.config.get("request_timeout", 60))
        self.max_retries = int(self.config.get("max_retries", 2))

        # Клиент нового SDK (если доступен)
        self._client: Optional["OpenAI"] = None
        if _HAS_OAI_CLIENT:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception:
                self._client = None

        print(f"✅ Используется OpenAI. Модель: {self.openai_model}")

    # ---------- Публичные методы ----------

    def chat(self, prompt: str, system_msg: str = "Ты — Aideon, самообучающийся AI.") -> str:
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
        return self._chat_call(messages)

    def analyze_code(self, code_text: str, file_path: Optional[str] = None) -> str:
        chunks = self._split_into_chunks(code_text, self.max_context_tokens)
        if len(chunks) <= 1:
            return self._analyze_single_chunk(chunks[0], file_path)

        combined: Dict[str, str] = {k: "" for k in ["chat", "problems", "plan", "process", "result", "code"]}

        for i, chunk_text in enumerate(chunks, 1):
            label = f"{file_path or 'без имени'} [chunk {i}/{len(chunks)}]"
            result_str = self._analyze_single_chunk(chunk_text, label)

            try:
                parsed = json.loads(result_str)
                for key in combined:
                    if key in parsed and isinstance(parsed[key], str):
                        combined[key] += f"\n\n[CHUNK {i}] {parsed[key]}"
            except json.JSONDecodeError:
                combined["chat"] += f"\n\n[CHUNK {i} ERROR]\n{result_str}"

        return json.dumps(combined, ensure_ascii=False, indent=2)

    # ---------- Внутренние методы ----------

    def _analyze_single_chunk(self, code_chunk: str, file_path: Optional[str] = None) -> str:
        project_tree = self.file_manager.get_project_tree("app")
        context_prompt = (
            "Ты — Aideon, AI-ассистент по анализу кода.\n"
            f"Структура проекта:\n{project_tree}\n\n"
            f"Анализируй код:\n{code_chunk}\n\n"
            "Ответ строго в JSON-формате:\n"
            "{\n"
            '  "chat": "...",\n'
            '  "problems": "...",\n'
            '  "plan": "...",\n'
            '  "process": "...",\n'
            '  "result": "...",\n'
            '  "code": "..." \n'
            "}\n"
            "Без пояснений вне JSON."
        )

        messages = [
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"},
        ]
        return self._chat_call(messages)

    def generate_code_star_coder(self, prompt_text: str) -> str:
        return "❌ Локальные модели отключены. Используйте OpenAI."

    def _split_into_chunks(self, text: str, max_ctx: int) -> List[str]:
        words = text.strip().split()
        if not words:
            return [""]
        if len(words) <= max_ctx:
            return [" ".join(words)]
        return [" ".join(words[i:i + max_ctx]) for i in range(0, len(words), max_ctx)]

    # ---------- Единая точка вызова OpenAI (без Responses API) ----------

    def _chat_call(self, messages: List[Dict[str, str]]) -> str:
        """
        Стабильный путь: только chat.completions (новый SDK) + фолбэк на старый SDK.
        Убрали Responses API, чтобы не ловить 400 'messages[...].content[0].type'.
        """
        last_err: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # Новый SDK (рекомендуемый путь)
                if self._client is not None and hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
                    resp = self._client.chat.completions.create(
                        model=self.openai_model,
                        messages=messages,
                        temperature=self.temperature,
                        timeout=self.request_timeout,
                    )
                    return (resp.choices[0].message.content or "").strip()

                # Старый SDK — совместимость
                if openai is not None:
                    openai.api_key = self.api_key
                    response = openai.ChatCompletion.create(
                        model=self.openai_model,
                        messages=messages,
                        temperature=self.temperature,
                        request_timeout=self.request_timeout,
                    )
                    return (response["choices"][0]["message"]["content"] or "").strip()

                return "Ошибка: OpenAI SDK не найден."

            except Exception as e:
                last_err = e
                err_txt = str(e)

                # Частые случаи — отдельные подсказки
                if "401" in err_txt or "invalid_api_key" in err_txt or "Incorrect API key" in err_txt:
                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
                if "missing required parameter" in err_txt.lower() and "messages" in err_txt.lower():
                    return (
                        "Ошибка: некорректный формат запроса для модели (400). "
                        "Проверьте формирование сообщений (role/content)."
                    )

                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))

        return f"Ошибка при обращении к OpenAI: {last_err}"