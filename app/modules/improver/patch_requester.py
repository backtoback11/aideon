# app/modules/improver/patch_requester.py
from __future__ import annotations

import re
from typing import Optional, Dict


class PatchRequester:
    """
    Генерирует строковый промпт для GPT на основании старого кода и плана улучшений.
    Ожидается, что модель вернёт ПОЛНЫЙ обновлённый текст файла.
    Также есть утилита extract_code() для извлечения чистого кода из «болтливых» ответов.
    """

    SYSTEM_MSG = (
        "Ты — помощник-программист. Обновляй код строго по плану улучшений, "
        "сохраняй работоспособность и смысл логики. Не ломай архитектуру, "
        "если это явно не требуется. Возвращай ПОЛНЫЙ ТЕКСТ ФАЙЛА. "
        "Без пояснений вокруг, без Markdown — только код."
    )

    def build_prompt(
        self,
        file_path: str,
        file_content: str,
        summary: str,
        plan_data: Dict
    ) -> str:
        """
        Возвращает ЕДИНУЮ строку для CodeAnalyzer.chat(prompt, system_msg=...).
        """
        plan = plan_data.get("plan", "").strip()
        comment = plan_data.get("comment", "").strip()

        return (
            f"Путь к файлу: {file_path}\n\n"
            f"Краткое описание (summary):\n{summary}\n\n"
            f"Комментарий:\n{comment}\n\n"
            f"ПЛАН ИЗМЕНЕНИЙ:\n{plan}\n\n"
            "Исходный код файла ниже. Обнови его, реализовав план, не ломая остальную систему. "
            "Верни ПОЛНЫЙ обновлённый файл, без Markdown и без дополнительных комментариев.\n\n"
            "----- НАЧАЛО ИСХОДНИКА -----\n"
            f"{file_content}\n"
            "----- КОНЕЦ ИСХОДНИКА -----\n"
        )

    # Опционально (для UI/логов): если нужно отрисовывать messages
    def build_messages(self, file_path: str, file_content: str, summary: str, plan_data: Dict) -> list[dict]:
        return [
            {"role": "system", "content": self.SYSTEM_MSG},
            {"role": "user", "content": self.build_prompt(file_path, file_content, summary, plan_data)},
        ]

    @staticmethod
    def extract_code(raw: Optional[str]) -> str:
        """
        Извлекает «чистый» код из ответа модели:
        - срезает ```блоки``` (```python ... ```),
        - удаляет BOM/невидимые символы,
        - убирает префиксы вроде 'Обновлённый код:'.
        """
        if not raw:
            return ""

        text = raw.strip()

        # 1) убрать ограждения ``` ```
        fence = re.compile(r"^```(?:\w+)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
        m = fence.match(text)
        if m:
            text = m.group(1).strip()

        # 2) убрать частые префиксы/лейблы
        text = re.sub(r"^(?:Обновл[её]нный код|Updated code|Code)\s*:\s*", "", text, flags=re.IGNORECASE)

        # 3) убрать BOM и неразрывные пробелы
        text = text.replace("\ufeff", "").replace("\u00A0", " ")

        return text


# 👇 Обёртка — унифицированный вызов из SelfImprover (при необходимости)
def request_code_patch(
    chatgpt,
    file_path: str,
    file_content: str,
    summary: str,
    plan_data: Dict
) -> Optional[Dict[str, str]]:
    """
    Запрашивает у GPT обновлённый код по плану. Возвращает {"code": "<новый_файл>"} или None.
    Совместимо с CodeAnalyzer.chat(prompt, system_msg=...).
    """
    requester = PatchRequester()
    prompt = requester.build_prompt(file_path, file_content, summary, plan_data)
    # Рекомендуется передавать строгий system_msg, чтобы модель не болтала
    raw = chatgpt.chat(prompt, system_msg=requester.SYSTEM_MSG)
    code = requester.extract_code(raw)
    return {"code": code} if code else None