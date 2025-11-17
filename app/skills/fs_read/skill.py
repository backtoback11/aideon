from __future__ import annotations
from typing import Optional
import os

from app.core.file_manager import FileManager
from app.logger import log_info, log_warning

def run(path: str) -> str:
    """
    Читать файл безопасно (только текст).
    """
    fm = FileManager()
    abs_path = os.path.abspath(path)
    text: Optional[str] = fm.read_file(abs_path)
    if text is None:
        log_warning(f"[fs.read] не удалось прочитать: {abs_path}")
        return ""
    log_info(f"[fs.read] {abs_path} ({len(text)} симв.)")
    return text