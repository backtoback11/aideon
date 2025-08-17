import json
from typing import Optional

class ImprovementPlanner:
    """
    Строит промт для GPT, чтобы получить план улучшений по саммери кода.
    Также извлекает JSON-ответ с ключами 'plan' и 'comment'.
    """

    def build_prompt(self, file_path: str, summary: str) -> list[dict]:
        return [
            {
                "role": "system",
                "content": (
                    "Ты — эксперт по улучшению Python-кода. "
                    "На вход ты получаешь краткое описание файла проекта. "
                    "Ответь, как можно улучшить логику, устойчивость, читаемость или архитектуру файла."
                )
            },
            {
                "role": "user",
                "content": (
                    f"Путь к файлу: {file_path}\n\n"
                    f"Описание файла:\n{summary}\n\n"
                    "Сформулируй предложения по улучшению. "
                    "Ответ строго в формате JSON:\n"
                    "{\"plan\": \"описание шагов\", \"comment\": \"суть изменений\"}"
                )
            }
        ]

    def extract_plan(self, gpt_response: str) -> Optional[dict]:
        """
        Пытается распарсить JSON-ответ и извлечь поля "plan" и "comment".
        Возвращает словарь или None при ошибке.
        """
        try:
            data = json.loads(gpt_response)
            if isinstance(data, dict) and "plan" in data and "comment" in data:
                return data
        except Exception:
            pass
        return None


# 👇 Обёртка-функция для использования с SelfImprover
def get_improvement_plan(chatgpt, file_path: str, summary: str) -> Optional[dict]:
    planner = ImprovementPlanner()
    messages = planner.build_prompt(file_path, summary)
    response = chatgpt.ask(messages)
    return planner.extract_plan(response)