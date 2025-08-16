import json
import openai

from app.utils import load_api_key
from app.core.file_manager import FileManager

class CodeAnalyzer:
    """
    Модуль для анализа и генерации кода с использованием GPT (OpenAI).
    Локальные модели отключены. Всё — через OpenAI.
    """

    def __init__(self, config=None, chat_panel=None):
        self.config = config or {}
        self.file_manager = FileManager()
        self.model_mode = "ChatGPT"
        self.api_key = load_api_key(self.config)
        self.openai_model = self.config.get("model_name", "gpt-4o")
        self.temperature = self.config.get("temperature", 0.7)
        self.max_context_tokens = self.config.get("max_context_tokens", 8192)
        self.chat_panel = chat_panel  # Для логов запросов/ответов (можно не использовать)

        print("✅ Используется ChatGPT (OpenAI).")

    def chat(self, prompt, system_msg="Ты — Aideon, самообучающийся AI."):
        """
        Свободный диалог с ChatGPT.
        prompt: str (user prompt) или list[dict] (готовый messages)
        """
        openai.api_key = self.api_key

        # Автоматически определяем формат prompt
        if isinstance(prompt, list):  # Готовый messages
            messages = prompt
        else:  # Просто строка — оборачиваем как обычно
            messages = [
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt}
            ]
        # Логируем для панели, если надо
        if self.chat_panel:
            self.chat_panel.add_gpt_request(messages)
        try:
            response = openai.ChatCompletion.create(
                model=self.openai_model,
                messages=messages,
                temperature=self.temperature
            )
            answer = response["choices"][0]["message"]["content"]
            if self.chat_panel:
                self.chat_panel.add_gpt_response(answer)
            return answer
        except Exception as e:
            error_msg = f"Ошибка при обращении к OpenAI: {e}"
            if self.chat_panel:
                self.chat_panel.add_gpt_response(error_msg)
            return error_msg

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
        return self.chat(
            [
                {"role": "system", "content": context_prompt},
                {"role": "user", "content": f"Анализируй код из файла {file_path}:\n{code_chunk}"}
            ]
        )

    def generate_code_star_coder(self, prompt_text):
        return (
            "❌ Локальная модель StarCoder временно отключена. "
            "Используйте ChatGPT для генерации кода."
        )

    def _split_into_chunks(self, text, max_ctx):
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