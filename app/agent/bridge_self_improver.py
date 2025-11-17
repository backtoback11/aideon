# app/agent/bridge_self_improver.py
from __future__ import annotations

from typing import Dict, Any, Optional

from app.logger import log_info, log_warning, log_error
from app.modules.self_improver import SelfImprover

# Ленивая опциональная инфраструктура
try:
    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
except Exception:
    FileManager = None             # type: ignore
    FileManagerConfig = None       # type: ignore

try:
    from app.modules.improver.patcher import CodePatcher  # type: ignore
except Exception:
    CodePatcher = None  # type: ignore


class SelfImproverBridge:
    """
    Мост между агентом и SelfImprover.
    Совместим:
      - старый стиль:  SelfImproverBridge(config, chat_panel=None)
      - новый стиль:   SelfImproverBridge(config, file_manager=fm, patcher=patcher, chat_panel=None)

    По умолчанию работает в diff-only (без авто-применения), включается через
    config["auto_apply_patches"]=True.
    """

    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        *,
        chat_panel=None,
        file_manager=None,
        patcher=None,
    ):
        self.config: Dict[str, Any] = dict(config or {})
        # По умолчанию — безопасный режим
        self.config.setdefault("auto_apply_patches", False)

        self.chat_panel = chat_panel
        self.fm = file_manager
        self.patcher = patcher

        # Если нам не передали FileManager — создадим дефолтный (не падаем, если модуль недоступен)
        if self.fm is None:
            if FileManager is not None:
                try:
                    # Совместимо со старыми/новыми сигнатурами FileManager()
                    self.fm = FileManager()  # type: ignore[call-arg]
                    log_info("[SelfImproverBridge] Создан дефолтный FileManager()")
                except Exception as e:
                    log_warning(f"[SelfImproverBridge] Не удалось создать FileManager(): {e}")
                    self.fm = None
            else:
                log_warning("[SelfImproverBridge] FileManager недоступен (импорт не удался)")

        # Если нет patcher — попробуем создать, если модуль доступен и есть fm
        if self.patcher is None and CodePatcher is not None and self.fm is not None:
            try:
                self.patcher = CodePatcher(file_manager=self.fm)  # type: ignore
                log_info("[SelfImproverBridge] Создан CodePatcher(file_manager=fm)")
            except Exception as e:
                log_warning(f"[SelfImproverBridge] Не удалось создать CodePatcher: {e}")
                self.patcher = None

        # Инициализируем SelfImprover с максимально полной сигнатурой,
        # при несовместимости — откатываемся к старой.
        self.si: Optional[SelfImprover] = None
        apply_flag: bool = bool(self.config.get("auto_apply_patches", False))

        init_attempts = [
            # Новый стиль, если поддерживается:
            dict(
                config=self.config,
                chat_panel=self.chat_panel,
                file_manager=self.fm,
                patcher=self.patcher,
                apply_patches_automatically=apply_flag,
            ),
            # Старый стиль (совместимость):
            dict(
                config=self.config,
                chat_panel=self.chat_panel,
                apply_patches_automatically=apply_flag,
            ),
        ]

        last_err: Optional[Exception] = None
        for kwargs in init_attempts:
            try:
                self.si = SelfImprover(**kwargs)  # type: ignore[arg-type]
                log_info("[SelfImproverBridge] SelfImprover инициализирован")
                break
            except TypeError as e:
                # Несовместимая сигнатура — пробуем следующий вариант
                last_err = e
            except Exception as e:
                last_err = e
                log_warning(f"[SelfImproverBridge] Ошибка инициализации SelfImprover: {e}")

        if self.si is None:
            # Если вообще не получилось — это критично для вызовов improve_project_once
            msg = f"Не удалось инициализировать SelfImprover: {last_err}"
            log_error(f"[SelfImproverBridge] {msg}")
            raise RuntimeError(msg)

    def improve_project_once(self) -> str:
        """
        Выполняет один проход SelfImprover и возвращает агрегированный лог/вывод.
        """
        if self.si is None:
            log_error("[SelfImproverBridge] SelfImprover не инициализирован")
            return ""

        log_info(
            "[SelfImproverBridge] Запускаю один цикл самоулучшения "
            f"(auto_apply={bool(self.config.get('auto_apply_patches', False))})"
        )

        output_chunks: list[str] = []
        try:
            for chunk in self.si.run_self_improvement():
                # chunk может быть как строкой, так и структурой — приводим к str
                output_chunks.append(str(chunk))
        except Exception as e:
            log_warning(f"[SelfImproverBridge] Ошибка во время improve_project_once: {e}")
            output_chunks.append(f"\n[bridge:error] {e}")

        return "\n".join(output_chunks)