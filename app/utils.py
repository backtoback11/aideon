import os

def load_api_key(config):
    """
    Возвращает API-ключ OpenAI из конфигурации или переменной окружения.
    """
    return config.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")