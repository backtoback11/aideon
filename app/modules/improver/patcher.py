# app/modules/improver/patcher.py
from __future__ import annotations

import os
import shutil
import difflib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, Any, Dict

from app.logger import log_info, log_error, log_warning

try:
    # Опциональная интеграция с централизованным менеджером файлов (если есть)
    from app.core.file_manager import FileManager as CoreFileManager  # type: ignore
except Exception:
    CoreFileManager = None  # не требуем наличия


class CodePatcher:
    """
    Применяет патчи к файлам:
    - делает резервную копию,
    - показывает/сохраняет diff,
    - записывает новый код,
    - сохраняет .diff отдельно,
    - сохраняет metadata о применённом патче (JSON).

    Обратная совместимость:
      - confirm_and_apply_patch(file_path, old_code, new_code) -> (backup_path, diff_path)
      - apply_patch_no_prompt(file_path, old_code, new_code, *, save_backup, save_diff, save_only, interactive_confirm)
      - _save_diff(file_path, diff_text) И _save_diff(file_path, old_code, new_code) — оба варианта поддержаны
    """

    def __init__(
        self,
        backup_dir: str = "app/backups",
        diff_dir: str = "app/patches",
        *,
        file_manager: Optional["CoreFileManager"] = None,  # опционально
        diffs_dirname_nested: bool = True,                 # складывать дифы по относительным подпапкам
        context_lines: int = 3
    ):
        self.backup_dir = Path(backup_dir)
        self.diff_dir = Path(diff_dir)
        self.fm = file_manager if CoreFileManager and isinstance(file_manager, CoreFileManager) else None
        self.diffs_dirname_nested = diffs_dirname_nested
        self.context_lines = int(context_lines)

        # гарантируем каталоги
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.diff_dir.mkdir(parents=True, exist_ok=True)

        log_info(
            f"[CodePatcher] init backup_dir={self.backup_dir} diff_dir={self.diff_dir} "
            f"core_fm={'on' if self.fm else 'off'}"
        )

    # ---------- Публичные методы ----------

    def confirm_and_apply_patch(self, file_path: str, old_code: str, new_code: str) -> Tuple[Optional[str], Optional[str]]:
        """
        Интерактивное применение патча с вопросом в консоли.
        Возвращает (backup_path, diff_path).
        """
        file_path = str(self._norm(file_path))
        diff_text = self._generate_diff(file_path, old_code, new_code)
        diff_path = self._save_diff(file_path, diff_text)  # совместимо с новой сигнатурой
        print(diff_text)

        choice = input("[CodePatcher] Применить патч? (y/n): ").strip().lower()
        if choice != "y":
            log_info(f"[CodePatcher] ❌ Патч для {file_path} отменён.")
            return None, diff_path

        backup_path = self._backup(file_path)
        self._write_code(file_path, new_code)
        self._save_metadata(file_path, old_code, new_code, diff_path, interactive=True)
        return backup_path, diff_path

    def apply_patch_no_prompt(
        self,
        file_path: str,
        old_code: str,
        new_code: str,
        *,
        save_backup: bool = True,
        save_diff: bool = True,
        # ↓↓↓ параметры для обратной совместимости с новыми вызовами
        save_only: Optional[bool] = None,
        interactive_confirm: Optional[bool] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Неинтерактивное применение патча — используется в авто-режимах.
        Возвращает (backup_path, diff_path).

        Аргументы:
          - save_backup: делать ли .bak перед записью
          - save_diff: сохранять ли diff-файл
          - save_only: (для совместимости) если True — НЕ перезаписывать файл, только сохранить diff
          - interactive_confirm: игнорируется (неинтерактивный метод), оставлен для совместимости
        """
        file_path = str(self._norm(file_path))

        # save_only имеет приоритет
        if isinstance(save_only, bool):
            if save_only:
                save_backup_effective = False
                apply_code = False
            else:
                save_backup_effective = save_backup
                apply_code = True
        else:
            save_backup_effective = save_backup
            apply_code = True

        diff_path = None
        if save_diff:
            # поддерживаем вызов _save_diff(file_path, old, new)
            diff_path = self._save_diff(file_path, old_code, new_code)

        backup_path = None
        if apply_code:
            if save_backup_effective:
                backup_path = self._backup(file_path)
            self._write_code(file_path, new_code)
            self._save_metadata(file_path, old_code, new_code, diff_path, interactive=False)
            log_info(f"[CodePatcher] ✅ Патч применён: {file_path}")
        else:
            log_info(f"[CodePatcher] 📝 Diff сохранён без применения патча: {file_path}")

        return backup_path, diff_path

    # ---------- Внутренние утилиты ----------

    def _backup(self, file_path: str) -> Optional[str]:
        """
        Создаёт копию целевого файла в backup_dir. Если файла нет — просто логируем.
        """
        src = Path(file_path)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = self.backup_dir / f"{src.name}.{ts}.bak"

        if not src.exists():
            log_warning(f"[CodePatcher] Бэкап пропущен: файл не найден для {src}")
            return None

        try:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(src), str(dst))
            log_info(f"[CodePatcher] 🧯 Бэкап создан: {dst}")
            return str(dst)
        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при создании бэкапа: {e}")
            return None

    def _write_code(self, file_path: str, new_code: str) -> None:
        """
        Пишем новый код. Если присутствует CoreFileManager — используем его атомарную запись.
        """
        p = Path(file_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            if self.fm:
                # атомарная запись через CoreFileManager
                self.fm.write_text(p, new_code)  # type: ignore[arg-type]
            else:
                with open(p, "w", encoding="utf-8", newline="") as f:
                    f.write(new_code)
            log_info(f"[CodePatcher] ✅ Код обновлён: {p}")
        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при записи файла '{p}': {e}")
            raise

    def _generate_diff(self, path: str, old_code: str, new_code: str) -> str:
        old_lines = (old_code or "").splitlines(keepends=True)
        new_lines = (new_code or "").splitlines(keepends=True)
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=path,
            tofile=f"{path} (updated)",
            n=self.context_lines,
            lineterm=""
        )
        return "\n".join(diff)

    def _save_diff(self, file_path: str, *args: Any) -> Optional[str]:
        """
        Бэкенд-совместимая функция сохранения diff.

        Варианты вызова:
          1) _save_diff(file_path, diff_text)
          2) _save_diff(file_path, old_code, new_code)

        Возвращает путь к сохранённому diff-файлу или None при ошибке.
        """
        try:
            if len(args) == 1:
                # Старый вызов: вторым параметром уже готовый diff_text
                diff_text = str(args[0])
            elif len(args) == 2:
                # Новый вызов: переданы old_code и new_code
                old_code, new_code = args
                diff_text = self._generate_diff(file_path, str(old_code), str(new_code))
            else:
                raise TypeError(f"_save_diff() ожидает 2 или 3 аргумента, получено: {1 + len(args)}")

            out_file = self._make_diff_output_path(file_path)
            out_file.parent.mkdir(parents=True, exist_ok=True)

            if self.fm:
                self.fm.write_text(out_file, diff_text)  # type: ignore[arg-type]
            else:
                with open(out_file, "w", encoding="utf-8", newline="") as f:
                    f.write(diff_text)

            log_info(f"[CodePatcher] 💾 Diff сохранён: {out_file}")
            return str(out_file)

        except Exception as e:
            log_error(f"[CodePatcher] ❌ Ошибка при сохранении diff: {e}")
            return None

    # ---------- Дополнительно: метаданные и пути ----------

    def _save_metadata(
        self,
        file_path: str,
        old_code: str,
        new_code: str,
        diff_path: Optional[str],
        interactive: bool
    ) -> None:
        """
        Сохраняем метаданные о применённом патче рядом с .diff:
        - change_id, timestamps
        - пути, размеры, хэши (если CoreFileManager доступен)
        - режим применения (interactive/auto)
        """
        try:
            change_id = f"{int(time.time())}"
            meta: Dict[str, Any] = {
                "change_id": change_id,
                "file": str(Path(file_path).resolve()),
                "diff_path": diff_path,
                "mode": "interactive" if interactive else "auto",
                "applied_at": datetime.now().isoformat(timespec="seconds"),
                "old_len": len(old_code or ""),
                "new_len": len(new_code or ""),
            }

            # Хэши, если есть CoreFileManager
            if self.fm:
                p = Path(file_path).resolve()
                try:
                    meta["new_hash_sha256"] = self.fm.compute_hash(p, algo="sha256")  # type: ignore[arg-type]
                except Exception:
                    pass

            meta_path = self._make_diff_output_path(file_path, suffix=".meta.json")
            meta_path.parent.mkdir(parents=True, exist_ok=True)

            payload = json.dumps(meta, ensure_ascii=False, indent=2)
            if self.fm:
                self.fm.write_text(meta_path, payload)  # type: ignore[arg-type]
            else:
                with open(meta_path, "w", encoding="utf-8", newline="") as f:
                    f.write(payload)

            log_info(f"[CodePatcher] 🧾 Metadata сохранена: {meta_path}")
        except Exception as e:
            log_warning(f"[CodePatcher] Не удалось сохранить metadata: {e}")

    def _make_diff_output_path(self, file_path: str, *, suffix: str = ".diff.txt") -> Path:
        """
        Генерация пути для diff/metadata:
        - Если diffs_dirname_nested=True и файл лежит внутри известной базы (sandbox или fm.base_dir),
          сохраняем в подпапках, повторяя структуру.
        - Иначе — в корне diff_dir.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        src = Path(file_path).resolve()

        # База для относительного пути
        base_candidates = []
        if self.fm:
            base_candidates.append(self.fm.base_dir)  # type: ignore[attr-defined]
        # Евристика: если файл расположен внутри app/, положим дифы зеркально
        base_candidates.append(Path.cwd())
        chosen_rel = None

        if self.diffs_dirname_nested:
            for base in base_candidates:
                try:
                    rel = src.relative_to(Path(base).resolve())
                    chosen_rel = rel
                    break
                except Exception:
                    continue

        if chosen_rel:
            # app/agent/x.py -> app/patches/app/agent/x.py.<ts>.diff.txt
            out_file = self.diff_dir / chosen_rel
            out_file = out_file.with_name(f"{out_file.name}.{ts}{suffix}")
        else:
            out_file = self.diff_dir / f"{src.name}.{ts}{suffix}"

        return out_file

    def _norm(self, p: str | os.PathLike) -> Path:
        return Path(p).expanduser().resolve()