from __future__ import annotations
from typing import List, Dict, Any
from app.logger import log_info, log_warning

class Executor:
    def __init__(self, skills, safety):
        self.skills = skills
        self.safety = safety

    def run(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for i, step in enumerate(steps, 1):
            skill_name = step["skill"]
            args = step.get("args", {})
            sk = self.skills.get(skill_name)
            if not sk:
                log_warning(f"[Executor] навык не найден: {skill_name}")
                results.append({"step": i, "status": "missing", "skill": skill_name})
                continue
            ok, reason = self.safety.check(sk.manifest, args)
            if not ok:
                results.append({"step": i, "status": "blocked", "skill": skill_name, "reason": reason})
                continue
            try:
                out = sk.fn(**args)
                results.append({"step": i, "status": "ok", "skill": skill_name, "output": out})
                log_info(f"[Executor] шаг {i} skill={skill_name} ok")
            except Exception as e:
                results.append({"step": i, "status": "error", "skill": skill_name, "error": str(e)})
        return results