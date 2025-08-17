# app/modules/analyzer.py
from __future__ import annotations

import json
import os
import time
from typing import Optional, List, Dict, Any

from app.core.file_manager import FileManager
from app.utils import load_api_key  # тянет ключ из ENV/.env/settings, ключи НЕ храним в репо

# Пытаемся использовать новый клиент OpenAI, иначе fallback на старый openai.*
try:
    from openai import OpenAI  # новый SDK (openai>=1.x)
    _HAS_OAI_CLIENT = True
except Exception:
    _HAS_OAI_CLIENT = False

# Старый SDK (openai<1.x)
try:
    import openai  # type: ignore
except Exception:  # pragma: no cover
    openai = None  # type: ignore


class CodeAnalyzer:
    """
    Модуль анализа/генерации кода через OpenAI.
    - Ключ берём из ENV/.env (см. load_api_key)
    - Имя модели: ENV OPENAI_MODEL > config["openai"]["model_name"] > config["model_name"] > "gpt-4o"
    - Поддержка нового и старого SDK, ретраи/таймауты.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.file_manager = FileManager()

        self.api_key = load_api_key(self.config)
        self.openai_model = self._resolve_model_name(self.config)
        self.temperature = float(self.config.get("temperature", 0.7))
        self.max_context_tokens = int(self.config.get("max_context_tokens", 8192))
        self.request_timeout = int(self.config.get("request_timeout", 60))
        self.max_retries = int(self.config.get("max_retries", 2))

        # Новый клиент, если доступен
        self._client: Optional["OpenAI"] = None
        if _HAS_OAI_CLIENT:
            try:
                self._client = OpenAI(api_key=self.api_key)
            except Exception:
                self._client = None

        print("✅ Используется ChatGPT (OpenAI).")

    # ---------- Публичные методы ----------

    def chat(self, prompt: str, system_msg: str = "Ты — Aideon, самообучающийся AI.") -> str:
        """
        Свободный диалог с ChatGPT.
        """
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
        return self._chat_call(messages)

    def analyze_code(self, code_text: str, file_path: Optional[str] = None) -> str:
        """
        Анализ кода (через OpenAI) с поддержкой chunk-обработки для больших файлов.
        Возвращает JSON-строку.
        """
        chunks = self._split_into_chunks(code_text, self.max_context_tokens)
        if len(chunks) <= 1:
            return self._analyze_single_chunk(chunks[0], file_path)

        combined: Dict[str, str] = {
            "chat": "", "problems": "", "plan": "",
            "process": "", "result": "", "code": ""
        }

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

    # ---------- Внутренние вспомогательные ----------

    def _analyze_single_chunk(self, code_chunk: str, file_path: Optional[str] = None) -> str:
        """
        Запрос к OpenAI для анализа отдельного чанка кода.
        """
        project_tree = self.file_manager.get_project_tree("app")
        context_prompt = (
            "Ты — Aideon, AI-ассистент по анализу кода.\n"
            f"Тебе дана структура проекта:\n{project_tree}\n\n"
            f"Анализируй следующий код:\n{code_chunk}\n\n"
            "Ответ строго в JSON-формате:\n"
            "{\n"
            '  "chat": "...",\n'
            '  "problems": "...",\n'
            '  "plan": "...",\n'
            '  "process": "...",\n'
            '  "result": "...",\n'
            '  "code": "..." \n'
            "}\n"
            "Не добавляй ничего, кроме JSON."
        )

        messages = [
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"},
        ]
        return self._chat_call(messages)

    def generate_code_star_coder(self, prompt_text: str) -> str:
        """
        Заглушка: локальные модели отключены.
        """
        return (
            "❌ Локальная модель StarCoder временно отключена. "
            "Используйте ChatGPT для генерации кода."
        )

    def _split_into_chunks(self, text: str, max_ctx: int) -> List[str]:
        """
        Грубое разбиение текста по количеству слов ~ контексту.
        """
        text = text.strip()
        if not text:
            return [""]

        words = text.split()
        if len(words) <= max_ctx:
            return [text]

        chunks: List[str] = []
        for i in range(0, len(words), max_ctx):
            chunks.append(" ".join(words[i:i + max_ctx]))
        return chunks

    def _resolve_model_name(self, cfg: Dict[str, Any]) -> str:
        """
        Приоритет: ENV OPENAI_MODEL > cfg['openai']['model_name'] > cfg['model_name'] > 'gpt-4o'
        """
        env_model = os.getenv("OPENAI_MODEL")
        if env_model:
            return env_model
        openai_cfg = cfg.get("openai")
        if isinstance(openai_cfg, dict) and openai_cfg.get("model_name"):
            return str(openai_cfg["model_name"])
        if cfg.get("model_name"):
            return str(cfg["model_name"])
        return "gpt-4o"

    # --- Приватный унифицированный вызов OpenAI с ретраями/таймаутами ---
    def _chat_call(self, messages: List[Dict[str, str]]) -> str:
        """
        Единая точка вызова OpenAI (новый клиент или fallback на старый API).
        Ретраи с экспоненциальной паузой. Возвращает строку-ответ или сообщение об ошибке.
        """
        last_err: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                # Новый SDK?
                if self._client is not None:
                    # 1) сначала пробуем Responses API (современнее)
                    if hasattr(self._client, "responses"):
                        try:
                            resp = self._client.responses.create(
                                model=self.openai_model,
                                input=messages,  # roles поддерживаются в новом API
                                temperature=self.temperature,
                                timeout=self.request_timeout,
                            )
                            # Вытаскиваем текст из первого message.content[0].text
                            if resp and resp.output and len(resp.output) > 0:
                                # Унификация: у разных версий поля отличаются; берём безопасно
                                first = resp.output[0]
                                # some SDKs: first.content[0].text
                                text = None
                                try:
                                    if hasattr(first, "content") and first.content:
                                        seg = first.content[0]
                                        text = getattr(seg, "text", None) or getattr(seg, "content", None)
                                except Exception:
                                    text = None
                                if isinstance(text, str) and text.strip():
                                    return text.strip()
                        except Exception as e_resp:
                            # Если responses не сработал — пробуем chat.completions
                            last_err = e_resp

                    # 2) chat.completions (совместимость)
                    if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
                        resp2 = self._client.chat.completions.create(
                            model=self.openai_model,
                            messages=messages,
                            temperature=self.temperature,
                            timeout=self.request_timeout,
                        )
                        return (resp2.choices[0].message.content or "").strip()

                # Старый SDK
                if openai is not None:
                    openai.api_key = self.api_key
                    response = openai.ChatCompletion.create(
                        model=self.openai_model,
                        messages=messages,
                        temperature=self.temperature,
                        request_timeout=self.request_timeout,
                    )
                    return (response["choices"][0]["message"]["content"] or "").strip()

                # Если ни один путь не сработал
                return "Ошибка: OpenAI SDK не инициализирован."

            except Exception as e:
                last_err = e
                # Специальная обработка 401 (неверный ключ)
                err_str = str(e)
                if "401" in err_str or "invalid_api_key" in err_str or "Incorrect API key" in err_str:
                    return (
                        "Ошибка при обращении к OpenAI: неверный API-ключ (401). "
                        "Проверьте OPENAI_API_KEY в .env/окружении."
                    )
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))

        return f"Ошибка при обращении к OpenAI: {last_err}"