# app/modules/utils.py

"""
Вспомогательные функции: чтение ключа, копирование файлов, парсинг, и т.д.
"""

import os

def load_api_key(config):
    """
    Вытаскиваем API-ключ из:
    1) config['openai_api_key']
    2) переменной окружения OPENAI_API_KEY
    """
    key = config.get("openai_api_key", None)
    if not key:
        key = os.environ.get("OPENAI_API_KEY", "")
    return key