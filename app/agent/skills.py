from __future__ import annotations
import importlib
import json
import os
from typing import Dict, Any, Callable, Optional, List

from app.logger import log_info, log_warning, log_error

class Skill:
    def __init__(self, name: str, fn: Callable[..., Any], manifest: Dict[str, Any], module_path: str):
        self.name = name
        self.fn = fn
        self.manifest = manifest
        self.module_path = module_path  # для дебага/обновлений

class SkillRegistry:
    """
    Регистр навыков. Загружает скиллы из app/skills/<skill_name>/{manifest.json, skill.py}
    """
    def __init__(self, root: str = "app/skills"):
        self.root = root
        self.skills: Dict[str, Skill] = {}

    def load(self) -> None:
        if not os.path.isdir(self.root):
            log_warning(f"[SkillRegistry] нет директории {self.root}")
            return
        for d in sorted(os.listdir(self.root)):
            skill_dir = os.path.join(self.root, d)
            man = os.path.join(skill_dir, "manifest.json")
            imp = os.path.join(skill_dir, "skill.py")
            if os.path.isfile(man) and os.path.isfile(imp):
                try:
                    with open(man, "r", encoding="utf-8") as f:
                        m = json.load(f)
                    mod = importlib.import_module(f"app.skills.{d}.skill")
                    if not hasattr(mod, "run"):
                        log_warning(f"[SkillRegistry] в {imp} нет функции run(**kwargs)")
                        continue
                    name = m.get("name") or d
                    self.skills[name] = Skill(name, getattr(mod, "run"), m, imp)
                    log_info(f"[SkillRegistry] зарегистрирован навык: {name}")
                except Exception as e:
                    log_error(f"[SkillRegistry] ошибка загрузки {d}: {e}")

    def get(self, name: str) -> Optional[Skill]:
        return self.skills.get(name)

    def list(self) -> List[str]:
        return list(self.skills.keys())