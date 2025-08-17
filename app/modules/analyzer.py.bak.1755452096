import json
import time
from typing import Optional

from app.utils import load_api_key
from app.core.file_manager import FileManager

# Пытаемся использовать новый клиент OpenAI, иначе fallback на старый openai.*
try:
    from openai import OpenAI  # новый SDK
    _HAS_OAI_CLIENT = True
except Exception:
    _HAS_OAI_CLIENT = False

import openai  # на случай старого SDK


class CodeAnalyzer:
    """
    Модуль для анализа и генерации кода с использованием GPT (OpenAI).
    Локальные модели отключены. Всё — через OpenAI.
    """

    def __init__(self, config=None):
        self.config = config or {}
        self.file_manager = FileManager()

        self.model_mode = "ChatGPT"
        self.api_key = load_api_key(self.config)
        self.openai_model = self.config.get("model_name", "gpt-4o")
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

    def chat(self, prompt, system_msg="Ты — Aideon, самообучающийся AI."):
        """
        Свободный диалог с ChatGPT.
        """
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]
        return self._chat_call(messages)

    def analyze_code(self, code_text, file_path=None):
        """
        Анализ кода (через OpenAI) с поддержкой chunk-обработки для больших файлов.
        """
        chunks = self._split_into_chunks(code_text, self.max_context_tokens)
        if len(chunks) <= 1:
            return self._analyze_single_chunk(chunks[0], file_path)

        combined = {
            "chat": "", "problems": "", "plan": "",
            "process": "", "result": "", "code": ""
        }

        for i, chunk_text in enumerate(chunks, 1):
            label = f"{file_path or 'без имени'} [chunk {i}/{len(chunks)}]"
            result_str = self._analyze_single_chunk(chunk_text, label)

            try:
                parsed = json.loads(result_str)
                for key in combined:
                    if key in parsed:
                        combined[key] += f"\n\n[CHUNK {i}] {parsed[key]}"
            except json.JSONDecodeError:
                combined["chat"] += f"\n\n[CHUNK {i} ERROR]\n{result_str}"

        return json.dumps(combined, ensure_ascii=False, indent=2)

    def _analyze_single_chunk(self, code_chunk, file_path=None):
        """
        Запрос к OpenAI для анализа отдельного чанка кода.
        """
        project_tree = self.file_manager.get_project_tree("app")
        context_prompt = (
            "Ты — Aideon, AI-ассистент по анализу кода.\n"
            f"Тебе дана структура проекта:\n{project_tree}\n\n"
            f"Анализируй следующий код:\n{code_chunk}\n\n"
            "Ответ в JSON-формате:\n"
            "{\n"
            "  \"chat\": \"...\",\n"
            "  \"problems\": \"...\",\n"
            "  \"plan\": \"...\",\n"
            "  \"process\": \"...\",\n"
            "  \"result\": \"...\",\n"
            "  \"code\": \"...\"\n"
            "}\n"
            "Не добавляй ничего, кроме JSON."
        )

        messages = [
            {"role": "system", "content": context_prompt},
            {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"},
        ]
        return self._chat_call(messages)

    def generate_code_star_coder(self, prompt_text):
        """
        Заглушка для локальной генерации (StarCoder отключён).
        """
        return (
            "❌ Локальная модель StarCoder временно отключена. "
            "Используйте ChatGPT для генерации кода."
        )

    def _split_into_chunks(self, text, max_ctx):
        """
        Разделение текста на чанки по лимиту токенов/слов (очень грубо — по словам).
        """
        text = text.strip()
        if not text:
            return [""]

        words = text.split()
        if len(words) <= max_ctx:
            return [text]

        chunks = []
        for i in range(0, len(words), max_ctx):
            chunks.append(" ".join(words[i:i + max_ctx]))
        return chunks

    # --- Приватный унифицированный вызов OpenAI с ретраями/таймаутами ---
    def _chat_call(self, messages):
        """
        Единая точка вызова OpenAI (новый клиент или fallback на старый API).
        Ретраи с экспоненциальной паузой. Возвращает строку-ответ или сообщение об ошибке.
        """
        last_err = None
        for attempt in range(self.max_retries + 1):
            try:
                if self._client is not None:
                    # Новый SDK
                    resp = self._client.chat.completions.create(
                        model=self.openai_model,
                        messages=messages,
                        temperature=self.temperature,
                        timeout=self.request_timeout,
                    )
                    return (resp.choices[0].message.content or "").strip()
                else:
                    # Старый SDK совместимость
                    openai.api_key = self.api_key
                    response = openai.ChatCompletion.create(
                        model=self.openai_model,
                        messages=messages,
                        temperature=self.temperature,
                        request_timeout=self.request_timeout,
                    )
                    return (response["choices"][0]["message"]["content"] or "").strip()
            except Exception as e:
                last_err = e
                if attempt < self.max_retries:
                    time.sleep(1.5 * (attempt + 1))
        return f"Ошибка при обращении к OpenAI: {last_err}"
