import os
import shutil
import difflib
from datetime import datetime

from app.logger import log_info, log_error

class CodePatcher:
    """
    Применяет патчи к файлам:
    - делает резервную копию,
    - показывает diff,
    - записывает новый код,
    - сохраняет .diff отдельно.
    """

    def __init__(self, backup_dir="app/backups", diff_dir="app/patches"):
        self.backup_dir = backup_dir
        self.diff_dir = diff_dir
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.diff_dir, exist_ok=True)

    def confirm_and_apply_patch(self, file_path, old_code, new_code):
        """
        Показывает diff и предлагает применить изменения.
        """
        diff = self._generate_diff(file_path, old_code, new_code)
        self._save_diff(file_path, diff)
        print(diff)

        choice = input("[CodePatcher] Применить патч? (y/n): ").strip().lower()
        if choice != "y":
            log_info(f"[CodePatcher] ❌ Патч для {file_path} отменён.")
            return

        self._backup(file_path)
        self._write_code(file_path, new_code)

    def _backup(self, file_path):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        dst = os.path.join(self.backup_dir, f"{filename}.{ts}.bak")
        try:
            shutil.copy2(file_path, dst)
            log_info(f"[CodePatcher] 🧯 Бэкап создан: {dst}")
        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при создании бэкапа: {e}")

    def _write_code(self, file_path, new_code):
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(new_code)
            log_info(f"[CodePatcher] ✅ Код обновлён: {file_path}")
        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при записи файла: {e}")

    def _generate_diff(self, path, old_code, new_code):
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines, new_lines,
            fromfile=path,
            tofile=f"{path} (updated)",
            lineterm=""
        )
        return "\n".join(diff)

    def _save_diff(self, file_path, diff_text):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.basename(file_path)
        diff_file = os.path.join(self.diff_dir, f"{filename}.{ts}.diff.txt")
        try:
            with open(diff_file, "w", encoding="utf-8") as f:
                f.write(diff_text)
            log_info(f"[CodePatcher] 💾 Diff сохранён: {diff_file}")
        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при сохранении diff: {e}")