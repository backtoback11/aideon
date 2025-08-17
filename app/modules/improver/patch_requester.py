from typing import Optional

class PatchRequester:
    """
    Генерирует промт для GPT на основании старого кода и плана улучшений.
    Возвращает новый код в виде единого файла.
    """

    def build_prompt(
        self,
        file_path: str,
        file_content: str,
        summary: str,
        plan_data: dict
    ) -> list[dict]:
        plan = plan_data.get("plan", "")
        comment = plan_data.get("comment", "")

        return [
            {
                "role": "system",
                "content": (
                    "Ты — помощник-программист. "
                    "Твоя задача — обновить код на основе предложенного плана улучшений, "
                    "сохранив работоспособность и смысл логики. "
                    "Не удаляй важные участки без необходимости. "
                    "Не изменяй архитектуру, если это не требуется по плану. "
                    "Ответ должен быть полным обновлённым кодом файла."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Путь к файлу: {file_path}\n\n"
                    f"Краткое описание файла (summary):\n{summary}\n\n"
                    f"Комментарий от GPT:\n{comment}\n\n"
                    f"План улучшений:\n{plan}\n\n"
                    f"Исходный код файла:\n{file_content}\n\n"
                    "Пожалуйста, обнови этот код, реализовав указанный план. "
                    "Ответ должен содержать только обновлённый код файла."
                )
            }
        ]


def request_code_patch(
    chatgpt,
    file_path: str,
    file_content: str,
    summary: str,
    plan_data: dict
) -> Optional[dict]:
    """
    Запрашивает у GPT обновлённый код файла по плану.
    """
    requester = PatchRequester()
    messages = requester.build_prompt(file_path, file_content, summary, plan_data)
    response = chatgpt.ask(messages)
    return {"code": response} if response else None