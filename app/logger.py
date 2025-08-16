import os
import logging
from logging.handlers import RotatingFileHandler

# Директория и основные пути
LOG_DIR = "app/logs"
os.makedirs(LOG_DIR, exist_ok=True)

MAIN_LOG_FILE = os.path.join(LOG_DIR, "aideon.log")

# Цветной форматтер для консоли
class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[94m",    # Синий
        logging.INFO: "\033[92m",     # Зеленый
        logging.WARNING: "\033[93m",  # Желтый
        logging.ERROR: "\033[91m",    # Красный
        logging.CRITICAL: "\033[95m", # Фиолетовый
    }
    RESET = "\033[0m"

    def format(self, record):
        color = self.COLORS.get(record.levelno, "")
        return f"{color}{super().format(record)}{self.RESET}"

# Форматы
log_format = "%(asctime)s | %(levelname)s | %(message)s"
formatter = logging.Formatter(log_format)
color_formatter = ColorFormatter(log_format)

# Главный логгер
logger = logging.getLogger("Aideon")
logger.setLevel(logging.INFO)

# Консольный вывод
console_handler = logging.StreamHandler()
console_handler.setFormatter(color_formatter)
logger.addHandler(console_handler)

# Главный файл логов с ротацией
file_handler = RotatingFileHandler(MAIN_LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Отдельные файлы по уровню логов
for level_name, file_name in [("error", "error.log"), ("warning", "warning.log"), ("info", "info.log")]:
    handler = logging.FileHandler(os.path.join(LOG_DIR, file_name), encoding="utf-8")
    handler.setLevel(getattr(logging, level_name.upper()))
    handler.setFormatter(formatter)
    logger.addHandler(handler)

# Упрощённые функции
def log_info(msg): logger.info(msg)
def log_warning(msg): logger.warning(msg)
def log_error(msg): logger.error(msg)