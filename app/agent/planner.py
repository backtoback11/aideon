from __future__ import annotations
from typing import List, Dict, Any

class Planner:
    """
    Простейший планировщик: превращает цели в список шагов (скиллов).
    Позже сюда можно внедрить ReAct/ToT/LLM-планирование.
    """
    def make_plan(self, goals: List[str], state: Dict[str, Any]) -> List[Dict[str, Any]]:
        steps: List[Dict[str, Any]] = []
        for g in goals:
            if g == "collect_project_context":
                steps.append({"skill": "fs.read", "args": {"path": "README.md"}, "why": "получить контекст проекта"})
            # добавляй другие правила
        return steps