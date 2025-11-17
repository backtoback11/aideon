# app/agent/agent.py
from __future__ import annotations

from typing import Dict, Any, List, Optional, Callable
import json

from app.logger import log_info, log_warning, log_error
from app.agent.capabilities import CapabilityDiscovery
from app.agent.skills import SkillRegistry
from app.agent.safety import SafetyGuardian
from app.agent.planner import Planner
from app.agent.executor import Executor


class AideonAgent:
    """
    Единая точка: сканировать возможности, загрузить навыки, построить план и выполнить.

    Совместимость:
      - старый стиль: AideonAgent(policy_path="app/agent/policy_default.json")
      - новый стиль:  AideonAgent(policy_path=..., file_manager=fm, improver_bridge=bridge, config=cfg)

    Добавлены шорткаты:
      - run_autonomous(goal: str, max_steps: int = 5) -> Dict[str, Any]
      - plan_high_level(goal: str) -> Any
    И адаптер для planner: planner.build_high_level_plan(goal) доступен всегда.
    """

    def __init__(
        self,
        policy_path: str = "app/agent/policy_default.json",
        *,
        file_manager: Optional[Any] = None,
        improver_bridge: Optional[Any] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.config: Dict[str, Any] = dict(config or {})
        self.file_manager = file_manager
        self.improver_bridge = improver_bridge

        # --- Базовые компоненты
        self.discovery = CapabilityDiscovery()
        self.registry = SkillRegistry()
        self.planner = Planner()

        # --- Политика безопасности
        try:
            with open(policy_path, "r", encoding="utf-8") as f:
                policy = json.load(f)
        except Exception as e:
            log_warning(f"[Agent] policy не прочитан ({e}), используем дефолт.")
            policy = {"profile": "restricted", "net_disabled": True, "allow_shell": False}
        self.guard = SafetyGuardian(policy)

        # --- Исполнитель (совместимость со старыми/новыми сигнатурами)
        executor_created = False
        last_err: Optional[Exception] = None

        # Попытка c расширенными зависимостями
        try:
            self.executor = Executor(
                self.registry,
                self.guard,
                file_manager=self.file_manager,
                improver_bridge=self.improver_bridge,
                config=self.config,
            )  # type: ignore[call-arg]
            executor_created = True
        except TypeError as e:
            # Старый Executor не принимал расширенные kwargs — откатываемся
            last_err = e
        except Exception as e:
            last_err = e

        if not executor_created:
            try:
                self.executor = Executor(self.registry, self.guard)  # type: ignore[call-arg]
                executor_created = True
                if last_err:
                    log_warning(f"[Agent] Executor создан в режиме совместимости: {last_err}")
            except Exception as e:
                log_error(f"[Agent] Не удалось создать Executor: {e}")
                raise

        # --- Адаптер для planner: гарантируем build_high_level_plan(goal)
        if not hasattr(self.planner, "build_high_level_plan"):
            def _build_high_level_plan(goal: str):
                state = self.boot()
                return self.planner.make_plan([goal], state)  # type: ignore[attr-defined]
            # привязываем как метод
            setattr(self.planner, "build_high_level_plan", _build_high_level_plan)  # type: ignore[attr-defined]

    # --------------------
    # Высокоуровневые API
    # --------------------
    def boot(self) -> Dict[str, Any]:
        caps = self.discovery.scan()
        self.registry.load()
        state = {
            "capabilities": [c.__dict__ for c in caps],
            "skills": self.registry.list(),
        }
        log_info(f"[Agent] загрузился: skills={len(state['skills'])}")
        return state

    def plan_high_level(self, goal: str) -> Any:
        """
        План для одной цели (обёртка над planner.make_plan / build_high_level_plan).
        """
        # если у planner уже есть новый метод
        blp: Optional[Callable[[str], Any]] = getattr(self.planner, "build_high_level_plan", None)  # type: ignore
        if callable(blp):
            return blp(goal)
        # совместимость со старыми Planner: make_plan(goals, state)
        state = self.boot()
        return self.planner.make_plan([goal], state)

    def run_autonomous(self, goal: str, max_steps: int = 5) -> Dict[str, Any]:
        """
        Быстрый автономный прогон: строит план под один goal и выполняет.
        max_steps оставлен для совместимости (если Executor его поддерживает).
        """
        state = self.boot()
        plan = self.planner.make_plan([goal], state)

        # Пытаемся вызвать Executor.run с max_steps, если поддерживается
        try:
            results = self.executor.run(plan, max_steps=max_steps)  # type: ignore[call-arg]
        except TypeError:
            results = self.executor.run(plan)

        return {"plan": plan, "results": results, "state": state}

    # --------------------
    # Старые методы (совм.)
    # --------------------
    def run_goals(self, goals: List[str]) -> Dict[str, Any]:
        state = self.boot()
        plan = self.planner.make_plan(goals, state)
        results = self.executor.run(plan)
        return {"plan": plan, "results": results, "state": state}