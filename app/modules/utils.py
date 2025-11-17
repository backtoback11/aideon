# app/modules/utils.py

"""
Вспомогательные функции: загрузка API-ключа, модели, параметров генерации.
Поддерживает ENV и config, есть дефолты.
"""

import os
from typing import Any, Dict, Optional, Union


def load_param(
    name: str,
    env_name: str,
    config: Optional[Dict[str, Any]],
    default: Union[str, float, int]
) -> Union[str, float, int]:
    """
    Универсальная загрузка параметров.
    Приоритет:
    1. Переменная окружения (env_name)
    2. config[name]
    3. default
    """
    env_val = os.getenv(env_name)
    if env_val is not None:
        # Если дефолт — число, пробуем преобразовать
        if isinstance(default, (float, int)):
            try:
                return type(default)(env_val)
            except (ValueError, TypeError):
                return default
        return env_val.strip()

    if config and name in config:
        return config[name]

    return default


def load_api_key(config: Optional[Dict[str, Any]] = None) -> str:
    """Загрузить API-ключ OpenAI."""
    return str(load_param("openai_api_key", "OPENAI_API_KEY", config, ""))


def load_model_name(config: Optional[Dict[str, Any]] = None) -> str:
    """Загрузить название модели (по умолчанию gpt-4o)."""
    return str(load_param("model_name", "OPENAI_MODEL", config, "gpt-4o"))


def load_temperature(config: Optional[Dict[str, Any]] = None) -> float:
    """Загрузить температуру генерации (по умолчанию 0.7)."""
    return float(load_param("temperature", "OPENAI_TEMPERATURE", config, 0.7))