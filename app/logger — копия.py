# app/logger.py
from __future__ import annotations

import os
import json
import logging
import contextvars
from typing import Optional
from logging.handlers import RotatingFileHandler

# ---------- Константы и пути ----------
DEFAULT_LOG_DIR = os.getenv("LOG_DIR", "app/logs")
MAIN_LOG_FILE = "aideon.log"
AGENT_JSON_FILE = "agent.jsonl"  # новый структурный лог для агента

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

# ---------- JSON-форматтер для агентских событий ----------
class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {
            "ts": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        # контекст агента
        aid = AGENT_CTX_AGENT_ID.get()
        rid = AGENT_CTX_RUN_ID.get()
        tid = AGENT_CTX_TASK_ID.get()
        if aid is not None:
            base["agent_id"] = aid
        if rid is not None:
            base["run_id"] = rid
        if tid is not None:
            base["task_id"] = tid

        # extra (если передали словарь через emit_* )
        extra_dict = getattr(record, "extra", None)
        if isinstance(extra_dict, dict):
            base.update(extra_dict)

        return json.dumps(base, ensure_ascii=False)

# ---------- Контекст агента (contextvars) ----------
AGENT_CTX_AGENT_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("agent_id", default=None)
AGENT_CTX_RUN_ID:   contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("run_id",   default=None)
AGENT_CTX_TASK_ID:  contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("task_id",  default=None)

# ---------- Глобальный синглтон логгера ----------
_LOGGER: Optional[logging.Logger] = None
_AGENT_HANDLER_ATTACHED = False  # чтобы не дублировать JSON-хендлер

def _validated_level_from_env() -> tuple[int, str]:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper().strip()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        # fallback и предупреждение в консоль на этапе первичной инициализации
        level_name = "INFO"
        level = logging.INFO
        print(f"[logger] WARNING: invalid LOG_LEVEL, fallback to INFO")
    return level, level_name

def setup_logging() -> logging.Logger:
    """
    Инициализация логирования:
      - уровень берём из ENV LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL), по умолчанию INFO
      - вывод в консоль (цветной)
      - вывод в файл app/logs/aideon.log (ротация 2MB x 3)
      - отдельные файлы info.log / warning.log / error.log
    Повторный вызов безопасен (хендлеры не дублируются).
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)

    level, level_name = _validated_level_from_env()

    logger = logging.getLogger("Aideon")
    logger.setLevel(level)
    logger.propagate = False  # чтобы не улетало в корневой логгер

    # Форматы
    fmt = "%(asctime)s | %(levelname)s | %(message)s"
    datefmt = "%Y-%m-%d %H:%M:%S"
    text_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
    color_formatter = ColorFormatter(fmt=fmt, datefmt=datefmt)

    # Проверка на наличие хендлеров — чтобы не дублировать
    if not logger.handlers:
        # Консоль (цвет)
        sh = logging.StreamHandler()
        sh.setLevel(level)
        sh.setFormatter(color_formatter)
        logger.addHandler(sh)

        # Главный файл (ротация)
        main_path = os.path.join(DEFAULT_LOG_DIR, MAIN_LOG_FILE)
        fh = RotatingFileHandler(main_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(text_formatter)
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
            h.setFormatter(text_formatter)
            logger.addHandler(h)

    _LOGGER = logger
    logger.debug("Логирование инициализировано (level=%s, dir=%s)", level_name, DEFAULT_LOG_DIR)
    return logger

def _get_logger() -> logging.Logger:
    return _LOGGER or setup_logging()

# ---------- Агентский JSON-хендлер (лениво подключаем) ----------
def _ensure_agent_json_handler() -> None:
    """
    Добавляет JSON-хендлер в logger один раз.
    Не трогаем существующие хендлеры → сохраняем совместимость.
    """
    global _AGENT_HANDLER_ATTACHED
    if _AGENT_HANDLER_ATTACHED:
        return
    logger = _get_logger()
    # отдельный файл с JSONL
    agent_path = os.path.join(DEFAULT_LOG_DIR, AGENT_JSON_FILE)
    jh = RotatingFileHandler(agent_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
    jh.setLevel(logging.INFO)  # события агента обычно на INFO
    jh.setFormatter(JSONFormatter(fmt="%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(jh)
    _AGENT_HANDLER_ATTACHED = True
    logger.debug("Agent JSON handler attached → %s", agent_path)

# ---------- Контекст и события агента ----------
def set_agent_context(agent_id: str | None = None, run_id: str | None = None, task_id: str | None = None) -> None:
    """
    Устанавливает контекст для JSON-событий агента.
    Безопасно вызывать много раз (значения можно обновлять/сбрасывать).
    """
    if agent_id is not None:
        AGENT_CTX_AGENT_ID.set(agent_id)
    if run_id is not None:
        AGENT_CTX_RUN_ID.set(run_id)
    if task_id is not None:
        AGENT_CTX_TASK_ID.set(task_id)

def emit_event(event: str, **fields) -> None:
    """
    Универсальная точка эмиссии JSON-событий.
    Пишет в отдельный agent.jsonl и в обычные текстовые логи (через info).
    """
    _ensure_agent_json_handler()
    logger = _get_logger()
    # кладём payload в record.extra, JSONFormatter его подхватит
    logger.info(event, extra={"extra": {"event": event, **fields}})

def emit_tool_call(tool: str, action: str, latency_ms: int | None = None, **fields) -> None:
    emit_event("tool_call", tool=tool, action=action, latency_ms=latency_ms, **fields)

def emit_plan_started(goal: str, **fields) -> None:
    emit_event("plan_started", goal=goal, **fields)

def emit_action(step: str, status: str = "started", **fields) -> None:
    emit_event("action", step=step, status=status, **fields)

def emit_plan_finished(result: str, **fields) -> None:
    emit_event("plan_finished", result=result, **fields)

def emit_agent_error(err: str, **fields) -> None:
    emit_event("error", error=err, **fields)

# ---------- Упрощённые функции (совместимость с существующим кодом) ----------
def log_debug(msg: str) -> None:
    _get_logger().debug(msg)

def log_info(msg: str) -> None:
    _get_logger().info(msg)

def log_warning(msg: str) -> None:
    _get_logger().warning(msg)

def log_error(msg: str) -> None:
    _get_logger().error(msg)