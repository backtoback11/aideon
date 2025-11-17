from __future__ import annotations
import os
from typing import Optional, Dict, Any

from app.core.file_manager import FileManager
from app.modules.improver.patcher import CodePatcher
from app.logger import log_info

def run(path: str, new_text: str, apply: bool = False) -> Dict[str, Any]:
    """
    По умолчанию — сохраняет только diff (apply=False).
    Если apply=True — перезаписывает файл, создает бэкап и diff.
    """
    fm = FileManager()
    cp = CodePatcher()
    abs_path = os.path.abspath(path)
    old_text: Optional[str] = fm.read_file(abs_path) or ""

    if not apply:
        # безопасный режим: только diff
        diff_path = cp._save_diff(abs_path, old_text, new_text)
        return {"mode": "diff-only", "diff_path": diff_path}

    # запись с бэкапом и diff
    backup_path, diff_path = cp.apply_patch_no_prompt(
        file_path=abs_path,
        old_code=old_text,
        new_code=new_text,
        save_backup=True,
        save_diff=True
    )
    log_info(f"[fs.write] применено apply=True path={abs_path}")
    return {"mode": "apply", "backup_path": backup_path, "diff_path": diff_path}