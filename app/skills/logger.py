# app/logger.py
from __future__ import annotations

import os
import logging
from typing import Optional
from logging.handlers import RotatingFileHandler

# ---------- Константы и пути ----------
DEFAULT_LOG_DIR = os.getenv("LOG_DIR", "app/logs")
MAIN_LOG_FILE = "aideon.log"

# ---------- Цветной форматтер для консоли ----------
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",    # Синий
        logging.INFO: "\033[92m",     # Зеленый
        logging.WARNING: "\033[93m",  # Желтый
        logging.ERROR: "\033[91m",    # Красный
        logging.CRITICAL: "\033[95m", # Фиолетовый
    }
    RESET = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        color = self.COLORS.get(record.levelno, "")
        base = super().format(record)
        return f"{color}{base}{self.RESET}"

# ---------- Глобальный синглтон логгера ----------
_LOGGER: Optional[logging.Logger] = None

def setup_logging() -> logging.Logger:
    """
    Инициализация логирования:
      - уровень берём из ENV LOG_LEVEL (DEBUG/INFO/WARNING/ERROR), по умолчанию INFO
      - вывод в консоль (цветной)
      - вывод в файл app/logs/aideon.log (ротация 2MB x 3)
      - отдельные файлы info.log / warning.log / error.log
    Повторный вызов безопасен (хендлеры не дублируются).
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)

    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger("Aideon")
    logger.setLevel(level)
    logger.propagate = False  # чтобы не улетало в корневой логгер

    # Форматы
    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    color_formatter = ColorFormatter(fmt=fmt, datefmt=datefmt)

    # Проверка на наличие хендлеров — чтобы не дублировать
    if not logger.handlers:
        # Консоль
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(color_formatter)
        logger.addHandler(sh)

        # Главный файл (ротация)
        main_path = os.path.join(DEFAULT_LOG_DIR, MAIN_LOG_FILE)
        fh = RotatingFileHandler(main_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Отдельные файлы по уровням
        per_level = [
            (logging.INFO,    "info.log"),
            (logging.WARNING, "warning.log"),
            (logging.ERROR,   "error.log"),
        ]
        for lvl, fname in per_level:
            path = os.path.join(DEFAULT_LOG_DIR, fname)
            h = logging.FileHandler(path, encoding="utf-8")
            h.setLevel(lvl)
            h.setFormatter(formatter)
            logger.addHandler(h)

    _LOGGER = logger
    logger.debug("Логирование инициализировано (level=%s, dir=%s)", level_name, DEFAULT_LOG_DIR)
    return logger

def _get_logger() -> logging.Logger:
    return _LOGGER or setup_logging()

# ---------- Упрощённые функции (совместимость с существующим кодом) ----------
def log_debug(msg: str) -> None:
    _get_logger().debug(msg)

def log_info(msg: str) -> None:
    _get_logger().info(msg)

def log_warning(msg: str) -> None:
    _get_logger().warning(msg)

def log_error(msg: str) -> None:
    _get_logger().error(msg)