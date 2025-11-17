# app/core/file_manager.py
from __future__ import annotations

import hashlib
import io
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Union

from app.logger import log_info, log_warning, log_error


@dataclass
class FileManagerConfig:
    base_dir: Path
    allowed_roots: Optional[List[Path]] = None          # если None — разрешаем только base_dir
    read_only_paths: Optional[List[Path]] = None        # список путей только для чтения
    backups_dirname: str = ".aideon_backups"
    create_missing_dirs: bool = True
    atomic_write: bool = True


# ---------- вспомогательные ----------

def _as_path_list(values: Optional[Iterable[Union[str, Path]]]) -> List[Path]:
    if not values:
        return []
    out: List[Path] = []
    for v in values:
        out.append(Path(v).expanduser().resolve())
    return out


def _project_root_from_here() -> Path:
    """
    Определяем корень репозитория по расположению этого файла:
    .../aideon_5.0/app/core/file_manager.py --> repo_root = parents[2]
    """
    return Path(__file__).resolve().parents[2]


class FileManager:
    """
    Централизованный менеджер файлов.
    Совместим со скиллами fs_read/fs_write, CodePatcher и агентом.

    Гарантии:
      - Нормализация путей.
      - Белый список allowed_roots (включая base_dir).
      - Опциональная atomic_write (через временный файл + rename()).
      - Бэкап старой версии файла перед записью.

    Обратная совместимость:
      - FileManager() без аргументов — берёт repo_root как base_dir.
      - FileManager(config=FileManagerConfig(...)) — как раньше.
      - FileManager(base_dir=..., allowed_roots=..., ...) — старыми kwargs.
    """

    def __init__(
        self,
        config: Optional[FileManagerConfig] = None,
        *,
        # legacy kwargs (необязательные)
        base_dir: Optional[Union[str, Path]] = None,
        allowed_roots: Optional[Iterable[Union[str, Path]]] = None,
        read_only_paths: Optional[Iterable[Union[str, Path]]] = None,
        backups_dirname: Optional[str] = None,
        create_missing_dirs: Optional[bool] = None,
        atomic_write: Optional[bool] = None,
    ):
        # Собираем итоговый конфиг
        if config is None:
            base = Path(base_dir).expanduser().resolve() if base_dir else _project_root_from_here()
            cfg = FileManagerConfig(
                base_dir=base,
                allowed_roots=_as_path_list(allowed_roots) if allowed_roots is not None else [base],
                read_only_paths=_as_path_list(read_only_paths) if read_only_paths is not None else [],
                backups_dirname=backups_dirname or ".aideon_backups",
                create_missing_dirs=True if create_missing_dirs is None else bool(create_missing_dirs),
                atomic_write=True if atomic_write is None else bool(atomic_write),
            )
        else:
            base = Path(config.base_dir).expanduser().resolve()
            cfg = FileManagerConfig(
                base_dir=base,
                allowed_roots=_as_path_list(allowed_roots) if allowed_roots is not None else (
                    [Path(p).expanduser().resolve() for p in (config.allowed_roots or [base])]
                ),
                read_only_paths=_as_path_list(read_only_paths) if read_only_paths is not None else (
                    [Path(p).expanduser().resolve() for p in (config.read_only_paths or [])]
                ),
                backups_dirname=backups_dirname or config.backups_dirname,
                create_missing_dirs=config.create_missing_dirs if create_missing_dirs is None else bool(create_missing_dirs),
                atomic_write=config.atomic_write if atomic_write is None else bool(atomic_write),
            )

        self.cfg = cfg
        self.base_dir = self._norm(cfg.base_dir)

        # Если allowed_roots не задан — используем только base_dir
        self.allowed_roots = [self._norm(p) for p in (cfg.allowed_roots or [self.base_dir])]
        # Гарантируем, что base_dir входит в allowed_roots
        if not any(str(self.base_dir).startswith(str(r)) or str(r).startswith(str(self.base_dir)) for r in self.allowed_roots):
            self.allowed_roots.append(self.base_dir)

        self.read_only_paths = [self._norm(p) for p in (cfg.read_only_paths or [])]
        self.backups_dir = self.base_dir / self.cfg.backups_dirname
        self.backups_dir.mkdir(parents=True, exist_ok=True)

        log_info(f"[FileManager] base_dir={self.base_dir}")
        log_info(f"[FileManager] allowed_roots={self.allowed_roots}")

    # ---------- path helpers ----------

    def _norm(self, p: os.PathLike | str) -> Path:
        return Path(p).expanduser().resolve()

    def _in_allowed_roots(self, p: Path) -> bool:
        ps = str(p)
        for root in self.allowed_roots:
            rs = str(root)
            if ps == rs or ps.startswith(rs + os.sep) or ps.startswith(rs + "/"):
                return True
        return False

    def _is_read_only(self, p: Path) -> bool:
        ps = str(p)
        for rp in self.read_only_paths:
            rs = str(rp)
            if ps == rs or ps.startswith(rs + os.sep) or ps.startswith(rs + "/"):
                return True
        return False

    def resolve(self, rel_or_abs: os.PathLike | str) -> Path:
        """
        Разрешаем путь с учётом allowed_roots.

        Правила:
          - Относительные пути всегда якорим к base_dir.
          - Абсолютные пути разрешаем, если они лежат в allowed_roots.
          - Иначе — PermissionError.
        """
        raw = Path(rel_or_abs)
        if not raw.is_absolute():
            p = self._norm(self.base_dir / raw)
        else:
            p = self._norm(raw)

        if not self._in_allowed_roots(p):
            raise PermissionError(f"Path {p} is outside allowed roots")

        return p

    # ---------- queries ----------

    def exists(self, path: os.PathLike | str) -> bool:
        try:
            return self.resolve(path).exists()
        except Exception:
            return False

    def is_file(self, path: os.PathLike | str) -> bool:
        return self.resolve(path).is_file()

    def is_dir(self, path: os.PathLike | str) -> bool:
        return self.resolve(path).is_dir()

    def list_files(self, root: os.PathLike | str, patterns: Optional[Iterable[str]] = None) -> List[Path]:
        root_p = self.resolve(root)
        if not root_p.exists():
            return []
        files: List[Path] = []
        if patterns:
            for pat in patterns:
                files.extend(root_p.rglob(pat))
        else:
            files = [p for p in root_p.rglob("*") if p.is_file()]
        return [self._norm(p) for p in files if self._in_allowed_roots(self._norm(p))]

    # ---------- IO ----------

    def read_text(self, path: os.PathLike | str, encoding: str = "utf-8") -> str:
        p = self.resolve(path)
        with p.open("r", encoding=encoding, newline="") as f:
            return f.read()

    def read_bytes(self, path: os.PathLike | str) -> bytes:
        p = self.resolve(path)
        with p.open("rb") as f:
            return f.read()

    def write_text(self, path: os.PathLike | str, data: str, encoding: str = "utf-8") -> Path:
        p = self.resolve(path)
        if self._is_read_only(p):
            raise PermissionError(f"Path {p} is read-only")

        parent = p.parent
        if self.cfg.create_missing_dirs:
            parent.mkdir(parents=True, exist_ok=True)

        # backup старой версии (если была)
        if p.exists():
            self._backup_file(p)

        if self.cfg.atomic_write:
            tmp_fd, tmp_name = tempfile.mkstemp(prefix=".aideon_tmp_", dir=str(parent))
            try:
                with io.open(tmp_fd, "w", encoding=encoding, newline="") as f:
                    f.write(data)
                os.replace(tmp_name, p)  # атомарная замена
            except Exception as e:
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass
                log_error(f"[FileManager] atomic write failed: {e}")
                raise
        else:
            with p.open("w", encoding=encoding, newline="") as f:
                f.write(data)

        log_info(f"[FileManager] wrote {p}")
        return p

    def write_bytes(self, path: os.PathLike | str, data: bytes) -> Path:
        p = self.resolve(path)
        if self._is_read_only(p):
            raise PermissionError(f"Path {p} is read-only")

        parent = p.parent
        if self.cfg.create_missing_dirs:
            parent.mkdir(parents=True, exist_ok=True)

        if p.exists():
            self._backup_file(p)

        if self.cfg.atomic_write:
            tmp_fd, tmp_name = tempfile.mkstemp(prefix=".aideon_tmp_", dir=str(parent))
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(data)
                os.replace(tmp_name, p)
            except Exception as e:
                try:
                    os.remove(tmp_name)
                except Exception:
                    pass
                log_error(f"[FileManager] atomic write (bytes) failed: {e}")
                raise
        else:
            with p.open("wb") as f:
                f.write(data)

        log_info(f"[FileManager] wrote (bytes) {p}")
        return p

    # ---------- utils ----------

    def ensure_dir(self, path: os.PathLike | str) -> Path:
        p = self.resolve(path)
        p.mkdir(parents=True, exist_ok=True)
        return p

    def copy(self, src: os.PathLike | str, dst: os.PathLike | str) -> None:
        sp = self.resolve(src)
        dp = self.resolve(dst)
        if sp.is_dir():
            shutil.copytree(sp, dp, dirs_exist_ok=True)
        else:
            dp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sp, dp)

    def compute_hash(self, path: os.PathLike | str, algo: str = "sha256") -> str:
        p = self.resolve(path)
        h = hashlib.new(algo)
        with p.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                h.update(chunk)
        return h.hexdigest()

    def _backup_file(self, path: Path) -> Optional[Path]:
        # Пытаемся хранить иерархию бэкапов относительно base_dir
        try:
            rel = path.relative_to(self.base_dir)
        except ValueError:
            rel = Path("_external_") / path.name

        backup_target = self.backups_dir / rel
        backup_target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, backup_target)
        log_info(f"[FileManager] backup -> {backup_target}")
        return backup_target


# ============================
# ✅ Совместимые алиасы/экспорт (строго в конце)
# ============================
CoreFileManager = FileManager
__all__ = ["FileManager", "CoreFileManager", "FileManagerConfig"]