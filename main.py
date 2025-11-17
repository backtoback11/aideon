#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# main.py

from __future__ import annotations

import sys
import json
import os
import traceback
from typing import Dict, Any, Optional

# 🔔 Логирование — максимально рано
from app.logger import setup_logging, log_info, log_warning, log_error, log_debug

# Qt HiDPI до создания QApplication (без QWidget)
try:
    from PyQt6.QtCore import QCoreApplication, Qt
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
except Exception:
    pass

# --- Опциональные агентные импорты (не ломаем, если их нет) ---
_AIDEON_AGENT_AVAILABLE = False
try:
    from app.agent.agent import AideonAgent            # type: ignore
    from app.agent.bridge_self_improver import SelfImproverBridge  # type: ignore
    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
    from app.modules.improver.patcher import CodePatcher  # type: ignore
    _AIDEON_AGENT_AVAILABLE = True
except Exception:
    AideonAgent = None              # type: ignore
    SelfImproverBridge = None       # type: ignore
    FileManager = None              # type: ignore
    FileManagerConfig = None        # type: ignore
    CodePatcher = None              # type: ignore


# ⬇️ Подхватываем .env РАНЬШЕ всего, чтобы окружение было доступно везде
def _load_dotenv_early() -> None:
    try:
        from dotenv import load_dotenv  # type: ignore
        repo_root = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(repo_root, ".env")
        loaded = load_dotenv(dotenv_path=env_path, override=True)
        if loaded:
            log_info(f".env загружен: {env_path}")
        else:
            log_warning(f".env не найден или пуст: {env_path} (это не ошибка, продолжаем)")
    except Exception as e:
        log_warning(f"Не удалось загрузить .env ранним этапом: {e}")


def _safe_load_json(path: str) -> Dict[str, Any]:
    """Безопасно читает JSON. Возвращает {} при любой ошибке."""
    try:
        if not os.path.exists(path):
            log_debug(f"Конфиг не найден: {path}")
            return {}
        if os.path.getsize(path) == 0:
            log_warning(f"Конфиг пустой (0 байт): {path}")
            return {}
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            log_info(f"Конфиг прочитан: {path} (ключей: {len(data)})")
            return data
        log_warning(f"Конфиг не dict, проигнорирован: {path}")
        return {}
    except Exception as e:
        log_warning(f"Не удалось прочитать JSON {path}: {e}")
        return {}


def _install_crash_hook() -> None:
    def _hook(exc_type, exc, tb):
        log_error("Необработанное исключение:\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
        sys.__excepthook__(exc_type, exc, tb)
    sys.excepthook = _hook


def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(base)
    merged.update(override or {})
    return merged


def _apply_env_overrides(cfg: Dict[str, Any]) -> None:
    env_model = os.getenv("OPENAI_MODEL")
    if env_model:
        old = cfg.get("model_name")
        cfg["model_name"] = env_model
        log_info(f"OPENAI_MODEL переопределил model_name: {old!r} → {env_model!r}")

    env_temp = os.getenv("OPENAI_TEMPERATURE")
    if env_temp:
        try:
            old_t = cfg.get("temperature")
            cfg["temperature"] = float(env_temp)
            log_info(f"OPENAI_TEMPERATURE переопределил temperature: {old_t!r} → {cfg['temperature']!r}")
        except ValueError:
            log_warning(f"Некорректный OPENAI_TEMPERATURE={env_temp!r}, оставляем {cfg.get('temperature')!r}")

    api_key = os.getenv("OPENAI_API_KEY") or cfg.get("openai_api_key")
    if api_key:
        head = str(api_key)[:6]
        tail = str(api_key)[-4:]
        log_info(f"OPENAI_API_KEY обнаружен (mask): {head}…{tail}")
    else:
        log_warning("OPENAI_API_KEY не найден ни в ENV, ни в config — запросы к OpenAI вернут 401")


def _make_agent(repo_root: str, cfg: Dict[str, Any]) -> Optional["AideonAgent"]:
    """Опциональная сборка агента. Возвращает None, если модулей нет/не подошла сигнатура."""
    if not _AIDEON_AGENT_AVAILABLE:
        log_warning("AideonAgent недоступен (модуль не найден). GUI продолжит работу без агента.")
        return None
    try:
        root_path = os.path.abspath(repo_root)
        base_dir = os.path.join(root_path)

        fm_cfg = FileManagerConfig(  # type: ignore
            base_dir=base_dir,
            allowed_roots=[base_dir],
            read_only_paths=[os.path.join(base_dir, ".git")],
            backups_dirname=".aideon_backups",
            create_missing_dirs=True,
            atomic_write=True,
        )
        fm = FileManager(fm_cfg)  # type: ignore

        patcher = CodePatcher(file_manager=fm)  # type: ignore

        # --- Гибкая инициализация SelfImproverBridge (в разных ветках разная сигнатура)
        bridge: Optional["SelfImproverBridge"] = None
        try:
            bridge = SelfImproverBridge(file_manager=fm, patcher=patcher)  # type: ignore
        except TypeError:
            try:
                bridge = SelfImproverBridge(patcher=patcher)  # type: ignore
            except Exception as e2:
                log_warning(f"SelfImproverBridge недоступен: {e2}")
                bridge = None

        policy_path = os.path.join(root_path, "app", "agent", "policy_default.json")

        # --- Гибкая инициализация AideonAgent
        agent: Optional["AideonAgent"] = None
        try:
            agent = AideonAgent(  # type: ignore
                file_manager=fm,
                improver_bridge=bridge,
                policy_path=policy_path,
                config=cfg
            )
        except TypeError:
            # ветка без file_manager в конструкторе
            agent = AideonAgent(  # type: ignore
                improver_bridge=bridge,
                policy_path=policy_path,
                config=cfg
            )
        log_info("AideonAgent инициализирован")
        return agent
    except Exception as e:
        log_warning(f"Не удалось инициализировать AideonAgent: {e}")
        return None


def _maybe_cli_agent(argv: list[str], repo_root: str, cfg: Dict[str, Any]) -> Optional[int]:
    """
    Неблокирующие CLI-команды агента (опционально).
    --agent-plan "<goal>"
    --agent-run "<goal>" [--steps N]
    """
    if not argv:
        return None

    def _pos(flag: str) -> Optional[int]:
        try:
            return argv.index(flag)
        except ValueError:
            return None

    i_plan = _pos("--agent-plan")
    i_run = _pos("--agent-run")
    if i_plan is None and i_run is None:
        return None

    agent = _make_agent(repo_root, cfg)
    if agent is None:
        log_error("Нельзя выполнить агентную CLI-команду: AideonAgent недоступен.")
        return 2

    if i_plan is not None:
        try:
            goal = argv[i_plan + 1]
        except Exception:
            log_error('Укажите цель после --agent-plan "..."')
            return 2
        # допустим, в агенте есть high-level planner; если нет — используйте .planner.make_plan
        plan = agent.planner.build_high_level_plan(goal=goal)  # type: ignore
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if i_run is not None:
        try:
            goal = argv[i_run + 1]
        except Exception:
            log_error('Укажите цель после --agent-run "..."')
            return 2
        steps = 5
        if "--steps" in argv:
            try:
                steps = int(argv[argv.index("--steps") + 1])
            except Exception:
                log_warning("Некорректный --steps, используем 5")
        result = agent.run_autonomous(goal=goal, max_steps=steps)  # type: ignore
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    return None


def _attach_agent_to_window(window, agent) -> None:
    """
    Универсальная попытка «подмешать» агента в уже созданное окно и потребовать отрисовать меню.
    Это позволяет показать пункт «Агент» даже если старый MainWindow не принимал agent в __init__.
    """
    try:
        if agent is None:
            return
        # сначала пробуем «официальный» сеттер
        if hasattr(window, "set_agent") and callable(getattr(window, "set_agent")):
            window.set_agent(agent)  # type: ignore
            log_info("Агент привязан к окну через set_agent()")
        else:
            # fallback — просто присваиваем поле
            setattr(window, "agent", agent)
            log_info("Агент присвоен в window.agent (fallback)")

        # просим окно создать/обновить меню агента (любой из методов, если есть)
        if hasattr(window, "ensure_agent_menu") and callable(getattr(window, "ensure_agent_menu")):
            window.ensure_agent_menu()  # type: ignore
            log_info("ensure_agent_menu() вызвано — меню агента должно появиться")
        elif hasattr(window, "_create_agent_menu") and callable(getattr(window, "_create_agent_menu")):
            window._create_agent_menu()  # type: ignore
            log_info("_create_agent_menu() вызвано — меню агента должно появиться")
        else:
            log_warning("В окне нет ensure_agent_menu/_create_agent_menu — проверьте реализацию MainWindow")
    except Exception as e:
        log_warning(f"Не удалось прикрепить агента к окну: {e}")


def main() -> None:
    # 0) Логи и краш-хук
    setup_logging()
    _install_crash_hook()
    log_info("=== Старт Aideon ===")

    # 1) .env как можно раньше
    _load_dotenv_early()

    # 2) Базовый корень репо
    repo_root = os.path.dirname(os.path.abspath(__file__))
    log_debug(f"Repo root: {repo_root}")

    # 3) Конфиги
    cfg: Dict[str, Any] = _safe_load_json(os.path.join(repo_root, "config.json"))
    cfg = _merge_configs(cfg, _safe_load_json(os.path.join(repo_root, "app", "configs", "settings.json")))

    # 4) ENV-переопределения + дефолты
    _apply_env_overrides(cfg)
    cfg.setdefault("model_name", "gpt-4o")
    cfg.setdefault("temperature", 0.7)
    log_info(f"Финальная конфигурация: model={cfg['model_name']!r}, temperature={cfg['temperature']!r}")

    # 5) Агентные CLI-команды (если есть — выполняем и выходим)
    cli_rc = _maybe_cli_agent(sys.argv[1:], repo_root, cfg)
    if isinstance(cli_rc, int):
        sys.exit(cli_rc)

    # 6) Запуск GUI: создаём QApplication СНАЧАЛА, лениво импортируем MainWindow ПОТОМ
    try:
        from PyQt6.QtWidgets import QApplication  # импорт тут, раньше QWidget не трогаем
        app = QApplication(sys.argv)

        try:
            from app.ui.main_window import MainWindow  # импорт только после QApplication
        except Exception as e:
            log_error(f"Ошибка импорта MainWindow: {e}")
            raise

        agent = _make_agent(repo_root, cfg)

        # Если старый MainWindow без параметра agent — fallback + принудительное добавление меню
        try:
            window = MainWindow(config=cfg, agent=agent)  # type: ignore[call-arg]
            # Если конструктор принял — всё равно попросим гарантировать меню
            _attach_agent_to_window(window, agent)
        except TypeError:
            log_warning("MainWindow не поддерживает параметр 'agent'. Создаём окно без него и прикрепляем позже.")
            window = MainWindow(config=cfg)  # type: ignore[call-arg]
            _attach_agent_to_window(window, agent)

        window.show()
        log_info("Qt-приложение запущено")
        rc = app.exec()
        log_info(f"Qt-приложение завершилось с кодом {rc}")
        sys.exit(rc)

    except Exception as e:
        log_error(f"Критическая ошибка запуска UI: {e}")
        raise


if __name__ == "__main__":
    main()