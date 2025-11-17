# 📝 Last Changes Digest

- Generated: 2025-11-17T22:32:33.445189Z
- Range: `Push diff: 4f36a38..88debd7`
- Files changed: **39**

## Changed files

```text
M	.gitignore
A	app/agent/__init__.py
A	app/agent/agent.py
A	app/agent/bridge_self_improver.py
A	app/agent/capabilities.py
A	app/agent/executor.py
A	app/agent/planner.py
A	app/agent/policy_default.json
A	app/agent/safety.py
A	app/agent/skills.py
M	app/configs/settings.json
M	app/core/file_manager.py
M	app/logger.py
A	"app/logger\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"
M	app/modules/analyzer.py
M	app/modules/fixer.py
A	app/modules/improver/ai_bug_fixer.py
M	app/modules/improver/improvement_planner.py
M	app/modules/improver/patch_requester.py
M	app/modules/improver/patcher.py
M	app/modules/improver/project_scanner.py
A	"app/modules/improver/project_scanner\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"
M	app/modules/self_improver.py
A	"app/modules/self_improver\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"
M	app/modules/utils.py
A	app/skills/__init__.py
A	app/skills/fs_read/manifest.json
A	app/skills/fs_read/skill.py
A	app/skills/fs_write/manifest.json
A	app/skills/fs_write/skill.py
A	app/skills/http_get/manifest.json
A	app/skills/http_get/skill.py
A	app/skills/logger.py
A	app/skills/shell_exec/manifest.json
A	app/skills/shell_exec/skill.py
M	app/ui/main_window.py
A	config.example.json
A	config.json.save
M	main.py
```

## Diffs (unified=0)

<details><summary>.gitignore</summary>

```diff
diff --git a/.gitignore b/.gitignore
index 676d1f0..2c9f87e 100644
--- a/.gitignore
+++ b/.gitignore
@@ -20,0 +21 @@ app/sandbox/
+config.json
```

</details>

<details><summary>app/agent/__init__.py</summary>

```diff
diff --git a/app/agent/__init__.py b/app/agent/__init__.py
new file mode 100644
index 0000000..137e708
--- /dev/null
+++ b/app/agent/__init__.py
@@ -0,0 +1,2 @@
+# пусто/или версия
+__all__ = []
\ No newline at end of file
```

</details>

<details><summary>app/agent/agent.py</summary>

```diff
diff --git a/app/agent/agent.py b/app/agent/agent.py
new file mode 100644
index 0000000..e6570b1
--- /dev/null
+++ b/app/agent/agent.py
@@ -0,0 +1,141 @@
+# app/agent/agent.py
+from __future__ import annotations
+
+from typing import Dict, Any, List, Optional, Callable
+import json
+
+from app.logger import log_info, log_warning, log_error
+from app.agent.capabilities import CapabilityDiscovery
+from app.agent.skills import SkillRegistry
+from app.agent.safety import SafetyGuardian
+from app.agent.planner import Planner
+from app.agent.executor import Executor
+
+
+class AideonAgent:
+    """
+    Единая точка: сканировать возможности, загрузить навыки, построить план и выполнить.
+
+    Совместимость:
+      - старый стиль: AideonAgent(policy_path="app/agent/policy_default.json")
+      - новый стиль:  AideonAgent(policy_path=..., file_manager=fm, improver_bridge=bridge, config=cfg)
+
+    Добавлены шорткаты:
+      - run_autonomous(goal: str, max_steps: int = 5) -> Dict[str, Any]
+      - plan_high_level(goal: str) -> Any
+    И адаптер для planner: planner.build_high_level_plan(goal) доступен всегда.
+    """
+
+    def __init__(
+        self,
+        policy_path: str = "app/agent/policy_default.json",
+        *,
+        file_manager: Optional[Any] = None,
+        improver_bridge: Optional[Any] = None,
+        config: Optional[Dict[str, Any]] = None,
+    ):
+        self.config: Dict[str, Any] = dict(config or {})
+        self.file_manager = file_manager
+        self.improver_bridge = improver_bridge
+
+        # --- Базовые компоненты
+        self.discovery = CapabilityDiscovery()
+        self.registry = SkillRegistry()
+        self.planner = Planner()
+
+        # --- Политика безопасности
+        try:
+            with open(policy_path, "r", encoding="utf-8") as f:
+                policy = json.load(f)
+        except Exception as e:
+            log_warning(f"[Agent] policy не прочитан ({e}), используем дефолт.")
+            policy = {"profile": "restricted", "net_disabled": True, "allow_shell": False}
+        self.guard = SafetyGuardian(policy)
+
+        # --- Исполнитель (совместимость со старыми/новыми сигнатурами)
+        executor_created = False
+        last_err: Optional[Exception] = None
+
+        # Попытка c расширенными зависимостями
+        try:
+            self.executor = Executor(
+                self.registry,
+                self.guard,
+                file_manager=self.file_manager,
+                improver_bridge=self.improver_bridge,
+                config=self.config,
+            )  # type: ignore[call-arg]
+            executor_created = True
+        except TypeError as e:
+            # Старый Executor не принимал расширенные kwargs — откатываемся
+            last_err = e
+        except Exception as e:
+            last_err = e
+
+        if not executor_created:
+            try:
+                self.executor = Executor(self.registry, self.guard)  # type: ignore[call-arg]
+                executor_created = True
+                if last_err:
+                    log_warning(f"[Agent] Executor создан в режиме совместимости: {last_err}")
+            except Exception as e:
+                log_error(f"[Agent] Не удалось создать Executor: {e}")
+                raise
+
+        # --- Адаптер для planner: гарантируем build_high_level_plan(goal)
+        if not hasattr(self.planner, "build_high_level_plan"):
+            def _build_high_level_plan(goal: str):
+                state = self.boot()
+                return self.planner.make_plan([goal], state)  # type: ignore[attr-defined]
+            # привязываем как метод
+            setattr(self.planner, "build_high_level_plan", _build_high_level_plan)  # type: ignore[attr-defined]
+
+    # --------------------
+    # Высокоуровневые API
+    # --------------------
+    def boot(self) -> Dict[str, Any]:
+        caps = self.discovery.scan()
+        self.registry.load()
+        state = {
+            "capabilities": [c.__dict__ for c in caps],
+            "skills": self.registry.list(),
+        }
+        log_info(f"[Agent] загрузился: skills={len(state['skills'])}")
+        return state
+
+    def plan_high_level(self, goal: str) -> Any:
+        """
+        План для одной цели (обёртка над planner.make_plan / build_high_level_plan).
+        """
+        # если у planner уже есть новый метод
+        blp: Optional[Callable[[str], Any]] = getattr(self.planner, "build_high_level_plan", None)  # type: ignore
+        if callable(blp):
+            return blp(goal)
+        # совместимость со старыми Planner: make_plan(goals, state)
+        state = self.boot()
+        return self.planner.make_plan([goal], state)
+
+    def run_autonomous(self, goal: str, max_steps: int = 5) -> Dict[str, Any]:
+        """
+        Быстрый автономный прогон: строит план под один goal и выполняет.
+        max_steps оставлен для совместимости (если Executor его поддерживает).
+        """
+        state = self.boot()
+        plan = self.planner.make_plan([goal], state)
+
+        # Пытаемся вызвать Executor.run с max_steps, если поддерживается
+        try:
+            results = self.executor.run(plan, max_steps=max_steps)  # type: ignore[call-arg]
+        except TypeError:
+            results = self.executor.run(plan)
+
+        return {"plan": plan, "results": results, "state": state}
+
+    # --------------------
+    # Старые методы (совм.)
+    # --------------------
+    def run_goals(self, goals: List[str]) -> Dict[str, Any]:
+        state = self.boot()
+        plan = self.planner.make_plan(goals, state)
+        results = self.executor.run(plan)
+        return {"plan": plan, "results": results, "state": state}
\ No newline at end of file
```

</details>

<details><summary>app/agent/bridge_self_improver.py</summary>

```diff
diff --git a/app/agent/bridge_self_improver.py b/app/agent/bridge_self_improver.py
new file mode 100644
index 0000000..3f060bc
--- /dev/null
+++ b/app/agent/bridge_self_improver.py
@@ -0,0 +1,134 @@
+# app/agent/bridge_self_improver.py
+from __future__ import annotations
+
+from typing import Dict, Any, Optional
+
+from app.logger import log_info, log_warning, log_error
+from app.modules.self_improver import SelfImprover
+
+# Ленивая опциональная инфраструктура
+try:
+    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
+except Exception:
+    FileManager = None             # type: ignore
+    FileManagerConfig = None       # type: ignore
+
+try:
+    from app.modules.improver.patcher import CodePatcher  # type: ignore
+except Exception:
+    CodePatcher = None  # type: ignore
+
+
+class SelfImproverBridge:
+    """
+    Мост между агентом и SelfImprover.
+    Совместим:
+      - старый стиль:  SelfImproverBridge(config, chat_panel=None)
+      - новый стиль:   SelfImproverBridge(config, file_manager=fm, patcher=patcher, chat_panel=None)
+
+    По умолчанию работает в diff-only (без авто-применения), включается через
+    config["auto_apply_patches"]=True.
+    """
+
+    def __init__(
+        self,
+        config: Optional[Dict[str, Any]] = None,
+        *,
+        chat_panel=None,
+        file_manager=None,
+        patcher=None,
+    ):
+        self.config: Dict[str, Any] = dict(config or {})
+        # По умолчанию — безопасный режим
+        self.config.setdefault("auto_apply_patches", False)
+
+        self.chat_panel = chat_panel
+        self.fm = file_manager
+        self.patcher = patcher
+
+        # Если нам не передали FileManager — создадим дефолтный (не падаем, если модуль недоступен)
+        if self.fm is None:
+            if FileManager is not None:
+                try:
+                    # Совместимо со старыми/новыми сигнатурами FileManager()
+                    self.fm = FileManager()  # type: ignore[call-arg]
+                    log_info("[SelfImproverBridge] Создан дефолтный FileManager()")
+                except Exception as e:
+                    log_warning(f"[SelfImproverBridge] Не удалось создать FileManager(): {e}")
+                    self.fm = None
+            else:
+                log_warning("[SelfImproverBridge] FileManager недоступен (импорт не удался)")
+
+        # Если нет patcher — попробуем создать, если модуль доступен и есть fm
+        if self.patcher is None and CodePatcher is not None and self.fm is not None:
+            try:
+                self.patcher = CodePatcher(file_manager=self.fm)  # type: ignore
+                log_info("[SelfImproverBridge] Создан CodePatcher(file_manager=fm)")
+            except Exception as e:
+                log_warning(f"[SelfImproverBridge] Не удалось создать CodePatcher: {e}")
+                self.patcher = None
+
+        # Инициализируем SelfImprover с максимально полной сигнатурой,
+        # при несовместимости — откатываемся к старой.
+        self.si: Optional[SelfImprover] = None
+        apply_flag: bool = bool(self.config.get("auto_apply_patches", False))
+
+        init_attempts = [
+            # Новый стиль, если поддерживается:
+            dict(
+                config=self.config,
+                chat_panel=self.chat_panel,
+                file_manager=self.fm,
+                patcher=self.patcher,
+                apply_patches_automatically=apply_flag,
+            ),
+            # Старый стиль (совместимость):
+            dict(
+                config=self.config,
+                chat_panel=self.chat_panel,
+                apply_patches_automatically=apply_flag,
+            ),
+        ]
+
+        last_err: Optional[Exception] = None
+        for kwargs in init_attempts:
+            try:
+                self.si = SelfImprover(**kwargs)  # type: ignore[arg-type]
+                log_info("[SelfImproverBridge] SelfImprover инициализирован")
+                break
+            except TypeError as e:
+                # Несовместимая сигнатура — пробуем следующий вариант
+                last_err = e
+            except Exception as e:
+                last_err = e
+                log_warning(f"[SelfImproverBridge] Ошибка инициализации SelfImprover: {e}")
+
+        if self.si is None:
+            # Если вообще не получилось — это критично для вызовов improve_project_once
+            msg = f"Не удалось инициализировать SelfImprover: {last_err}"
+            log_error(f"[SelfImproverBridge] {msg}")
+            raise RuntimeError(msg)
+
+    def improve_project_once(self) -> str:
+        """
+        Выполняет один проход SelfImprover и возвращает агрегированный лог/вывод.
+        """
+        if self.si is None:
+            log_error("[SelfImproverBridge] SelfImprover не инициализирован")
+            return ""
+
+        log_info(
+            "[SelfImproverBridge] Запускаю один цикл самоулучшения "
+            f"(auto_apply={bool(self.config.get('auto_apply_patches', False))})"
+        )
+
+        output_chunks: list[str] = []
+        try:
+            for chunk in self.si.run_self_improvement():
+                # chunk может быть как строкой, так и структурой — приводим к str
+                output_chunks.append(str(chunk))
+        except Exception as e:
+            log_warning(f"[SelfImproverBridge] Ошибка во время improve_project_once: {e}")
+            output_chunks.append(f"\n[bridge:error] {e}")
+
+        return "\n".join(output_chunks)
\ No newline at end of file
```

</details>

<details><summary>app/agent/capabilities.py</summary>

```diff
diff --git a/app/agent/capabilities.py b/app/agent/capabilities.py
new file mode 100644
index 0000000..7b66b2e
--- /dev/null
+++ b/app/agent/capabilities.py
@@ -0,0 +1,34 @@
+from __future__ import annotations
+from dataclasses import dataclass
+from typing import Dict, Any, List
+import platform
+import shutil
+import os
+
+from app.logger import log_info
+
+@dataclass
+class Capability:
+    name: str
+    present: bool
+    details: Dict[str, Any]
+
+class CapabilityDiscovery:
+    """
+    Лёгкое авто-обнаружение возможностей устройства.
+    Можно расширять плагинами (ROS, GPIO, камеры и т.д.)
+    """
+    def scan(self) -> List[Capability]:
+        caps: List[Capability] = []
+        caps.append(Capability("os", True, {
+            "system": platform.system(),
+            "release": platform.release(),
+            "machine": platform.machine(),
+            "python": platform.python_version(),
+        }))
+        caps.append(Capability("docker", shutil.which("docker") is not None, {}))
+        caps.append(Capability("git", shutil.which("git") is not None, {}))
+        caps.append(Capability("camera_dev", os.path.exists("/dev/video0"), {}))
+        caps.append(Capability("network", True, {"curl": shutil.which("curl") is not None}))
+        log_info(f"[CapabilityDiscovery] найдено {len(caps)} capability")
+        return caps
\ No newline at end of file
```

</details>

<details><summary>app/agent/executor.py</summary>

```diff
diff --git a/app/agent/executor.py b/app/agent/executor.py
new file mode 100644
index 0000000..5ca27a0
--- /dev/null
+++ b/app/agent/executor.py
@@ -0,0 +1,30 @@
+from __future__ import annotations
+from typing import List, Dict, Any
+from app.logger import log_info, log_warning
+
+class Executor:
+    def __init__(self, skills, safety):
+        self.skills = skills
+        self.safety = safety
+
+    def run(self, steps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
+        results: List[Dict[str, Any]] = []
+        for i, step in enumerate(steps, 1):
+            skill_name = step["skill"]
+            args = step.get("args", {})
+            sk = self.skills.get(skill_name)
+            if not sk:
+                log_warning(f"[Executor] навык не найден: {skill_name}")
+                results.append({"step": i, "status": "missing", "skill": skill_name})
+                continue
+            ok, reason = self.safety.check(sk.manifest, args)
+            if not ok:
+                results.append({"step": i, "status": "blocked", "skill": skill_name, "reason": reason})
+                continue
+            try:
+                out = sk.fn(**args)
+                results.append({"step": i, "status": "ok", "skill": skill_name, "output": out})
+                log_info(f"[Executor] шаг {i} skill={skill_name} ok")
+            except Exception as e:
+                results.append({"step": i, "status": "error", "skill": skill_name, "error": str(e)})
+        return results
\ No newline at end of file
```

</details>

<details><summary>app/agent/planner.py</summary>

```diff
diff --git a/app/agent/planner.py b/app/agent/planner.py
new file mode 100644
index 0000000..ff79021
--- /dev/null
+++ b/app/agent/planner.py
@@ -0,0 +1,15 @@
+from __future__ import annotations
+from typing import List, Dict, Any
+
+class Planner:
+    """
+    Простейший планировщик: превращает цели в список шагов (скиллов).
+    Позже сюда можно внедрить ReAct/ToT/LLM-планирование.
+    """
+    def make_plan(self, goals: List[str], state: Dict[str, Any]) -> List[Dict[str, Any]]:
+        steps: List[Dict[str, Any]] = []
+        for g in goals:
+            if g == "collect_project_context":
+                steps.append({"skill": "fs.read", "args": {"path": "README.md"}, "why": "получить контекст проекта"})
+            # добавляй другие правила
+        return steps
\ No newline at end of file
```

</details>

<details><summary>app/agent/policy_default.json</summary>

```diff
diff --git a/app/agent/policy_default.json b/app/agent/policy_default.json
new file mode 100644
index 0000000..070cf49
--- /dev/null
+++ b/app/agent/policy_default.json
@@ -0,0 +1,6 @@
+{
+  "profile": "restricted",
+  "net_disabled": false,
+  "allow_shell": false,
+  "fs_write_whitelist": []
+}
\ No newline at end of file
```

</details>

<details><summary>app/agent/safety.py</summary>

```diff
diff --git a/app/agent/safety.py b/app/agent/safety.py
new file mode 100644
index 0000000..773b12f
--- /dev/null
+++ b/app/agent/safety.py
@@ -0,0 +1,39 @@
+from __future__ import annotations
+from typing import Dict, Any, Tuple, List
+from app.logger import log_info
+
+class SafetyGuardian:
+    """
+    Мини-политика безопасности.
+    Политика = dict, например:
+      {
+        "profile": "restricted",
+        "net_disabled": true,
+        "allow_shell": false,
+        "fs_write_whitelist": ["README.md"]
+      }
+    """
+    def __init__(self, policy: Dict[str, Any]):
+        self.policy = policy or {}
+
+    def check(self, skill_manifest: Dict[str, Any], args: Dict[str, Any]) -> Tuple[bool, str]:
+        perms: List[str] = skill_manifest.get("permissions", [])
+        prof = self.policy.get("profile", "default")
+
+        # запрет сети
+        if self.policy.get("net_disabled") and any(p.startswith("net.") for p in perms):
+            return False, "Network disabled by policy"
+
+        # контроль shell
+        if not self.policy.get("allow_shell", False) and any(p == "proc.shell" for p in perms):
+            return False, "Shell execution disabled by policy"
+
+        # файловые записи
+        if any(p == "fs.write" for p in perms):
+            wl = set(self.policy.get("fs_write_whitelist", []))
+            path = str(args.get("path", ""))
+            if wl and path not in wl:
+                return False, f"Write denied for {path} (not in whitelist)"
+
+        log_info(f"[Safety] OK skill={skill_manifest.get('name')} profile={prof}")
+        return True, ""
\ No newline at end of file
```

</details>

<details><summary>app/agent/skills.py</summary>

```diff
diff --git a/app/agent/skills.py b/app/agent/skills.py
new file mode 100644
index 0000000..0f34afe
--- /dev/null
+++ b/app/agent/skills.py
@@ -0,0 +1,50 @@
+from __future__ import annotations
+import importlib
+import json
+import os
+from typing import Dict, Any, Callable, Optional, List
+
+from app.logger import log_info, log_warning, log_error
+
+class Skill:
+    def __init__(self, name: str, fn: Callable[..., Any], manifest: Dict[str, Any], module_path: str):
+        self.name = name
+        self.fn = fn
+        self.manifest = manifest
+        self.module_path = module_path  # для дебага/обновлений
+
+class SkillRegistry:
+    """
+    Регистр навыков. Загружает скиллы из app/skills/<skill_name>/{manifest.json, skill.py}
+    """
+    def __init__(self, root: str = "app/skills"):
+        self.root = root
+        self.skills: Dict[str, Skill] = {}
+
+    def load(self) -> None:
+        if not os.path.isdir(self.root):
+            log_warning(f"[SkillRegistry] нет директории {self.root}")
+            return
+        for d in sorted(os.listdir(self.root)):
+            skill_dir = os.path.join(self.root, d)
+            man = os.path.join(skill_dir, "manifest.json")
+            imp = os.path.join(skill_dir, "skill.py")
+            if os.path.isfile(man) and os.path.isfile(imp):
+                try:
+                    with open(man, "r", encoding="utf-8") as f:
+                        m = json.load(f)
+                    mod = importlib.import_module(f"app.skills.{d}.skill")
+                    if not hasattr(mod, "run"):
+                        log_warning(f"[SkillRegistry] в {imp} нет функции run(**kwargs)")
+                        continue
+                    name = m.get("name") or d
+                    self.skills[name] = Skill(name, getattr(mod, "run"), m, imp)
+                    log_info(f"[SkillRegistry] зарегистрирован навык: {name}")
+                except Exception as e:
+                    log_error(f"[SkillRegistry] ошибка загрузки {d}: {e}")
+
+    def get(self, name: str) -> Optional[Skill]:
+        return self.skills.get(name)
+
+    def list(self) -> List[str]:
+        return list(self.skills.keys())
\ No newline at end of file
```

</details>

<details><summary>app/configs/settings.json</summary>

```diff
diff --git a/app/configs/settings.json b/app/configs/settings.json
index 1bb92ec..cb50204 100644
--- a/app/configs/settings.json
+++ b/app/configs/settings.json
@@ -3,9 +3,3 @@
-  "temperature": 0.7,
-  "use_mps": false,
-
-  "openai": {
-    "model_name": "gpt-5.0"
-  },
-
-  "model_name": "gpt-5.0",
-
+  "model_name": "${OPENAI_MODEL}",
+  "temperature": ${OPENAI_TEMPERATURE},
+  "use_mps": ${USE_MPS},
@@ -16,0 +11,9 @@
+}
+
+{
+  "auto_bugfix": true,
+  "max_fix_cycles": 2,
+  "auto_apply_patches": false,
+  "include_exts": [".py"],
+  "exclude_dirs": ["app/logs", "app/patches", "app/backups", "venv", ".venv", "__pycache__"],
+  "sensitive_dirs": [ ]
```

</details>

<details><summary>app/core/file_manager.py</summary>

```diff
diff --git a/app/core/file_manager.py b/app/core/file_manager.py
index c30b476..d4f3259 100644
--- a/app/core/file_manager.py
+++ b/app/core/file_manager.py
@@ -0,0 +1,5 @@
+# app/core/file_manager.py
+from __future__ import annotations
+
+import hashlib
+import io
@@ -3,2 +8,16 @@ import shutil
-import json
-from PyQt6.QtWidgets import QFileDialog
+import tempfile
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Iterable, List, Optional, Union
+
+from app.logger import log_info, log_warning, log_error
+
+
+@dataclass
+class FileManagerConfig:
+    base_dir: Path
+    allowed_roots: Optional[List[Path]] = None          # если None — разрешаем только base_dir
+    read_only_paths: Optional[List[Path]] = None        # список путей только для чтения
+    backups_dirname: str = ".aideon_backups"
+    create_missing_dirs: bool = True
+    atomic_write: bool = True
@@ -6,6 +24,0 @@ from PyQt6.QtWidgets import QFileDialog
-# Набор исключаемых директорий
-EXCLUDED_DIRS = {
-    "venv", ".git", "__pycache__", "node_modules", "dist", "build",
-    "site-packages", ".idea", ".vs", ".vscode",
-    "sandbox"  # Чтобы не копировать саму себя
-}
@@ -13,5 +26 @@ EXCLUDED_DIRS = {
-# Набор исключаемых расширений
-EXCLUDED_EXTS = {
-    ".pyc", ".pyo", ".log", ".exe", ".dll", ".so", ".dylib",
-    ".zip", ".rar", ".7z", ".tar", ".gz"
-}
+# ---------- вспомогательные ----------
@@ -19,2 +28,7 @@ EXCLUDED_EXTS = {
-# Пример ограничения размера (в байтах)
-MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
+def _as_path_list(values: Optional[Iterable[Union[str, Path]]]) -> List[Path]:
+    if not values:
+        return []
+    out: List[Path] = []
+    for v in values:
+        out.append(Path(v).expanduser().resolve())
+    return out
@@ -22,2 +36,7 @@ MAX_FILE_SIZE = 2 * 1024 * 1024  # 2 MB
-# Ограничение на длину пути (примерно)
-MAX_PATH_LENGTH = 250
+
+def _project_root_from_here() -> Path:
+    """
+    Определяем корень репозитория по расположению этого файла:
+    .../aideon_5.0/app/core/file_manager.py --> repo_root = parents[2]
+    """
+    return Path(__file__).resolve().parents[2]
@@ -27,25 +46,38 @@ class FileManager:
-    def __init__(self, sandbox_path="app/sandbox", history_path="app/logs/history.json"):
-        """
-        Управляет загрузкой файлов / проектов в песочницу (sandbox),
-        формирует и сохраняет структуру проекта, ведёт историю загрузок.
-        """
-        self.sandbox_path = os.path.abspath(sandbox_path)
-        self.history_path = history_path
-        self.project_tree_path = "app/logs/project_tree.json"
-
-        os.makedirs(self.sandbox_path, exist_ok=True)
-        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
-
-        self._original_project_root = None  # Запоминаем корень исходного проекта
-
-    # ---------------------------------------------------------
-    # Диалоги выбора (файл / проект)
-    # ---------------------------------------------------------
-    def open_file_dialog(self, multiple=False):
-        """Вызывает системный диалог выбора файлов."""
-        if multiple:
-            files, _ = QFileDialog.getOpenFileNames(
-                None,
-                "Выберите файлы для анализа",
-                "",
-                "Все файлы (*);;Python Files (*.py)"
+    """
+    Централизованный менеджер файлов.
+    Совместим со скиллами fs_read/fs_write, CodePatcher и агентом.
+
+    Гарантии:
+      - Нормализация путей.
+      - Белый список allowed_roots (включая base_dir).
+      - Опциональная atomic_write (через временный файл + rename()).
+      - Бэкап старой версии файла перед записью.
+
+    Обратная совместимость:
+      - FileManager() без аргументов — берёт repo_root как base_dir.
+      - FileManager(config=FileManagerConfig(...)) — как раньше.
+      - FileManager(base_dir=..., allowed_roots=..., ...) — старыми kwargs.
+    """
+
+    def __init__(
+        self,
+        config: Optional[FileManagerConfig] = None,
+        *,
+        # legacy kwargs (необязательные)
+        base_dir: Optional[Union[str, Path]] = None,
+        allowed_roots: Optional[Iterable[Union[str, Path]]] = None,
+        read_only_paths: Optional[Iterable[Union[str, Path]]] = None,
+        backups_dirname: Optional[str] = None,
+        create_missing_dirs: Optional[bool] = None,
+        atomic_write: Optional[bool] = None,
+    ):
+        # Собираем итоговый конфиг
+        if config is None:
+            base = Path(base_dir).expanduser().resolve() if base_dir else _project_root_from_here()
+            cfg = FileManagerConfig(
+                base_dir=base,
+                allowed_roots=_as_path_list(allowed_roots) if allowed_roots is not None else [base],
+                read_only_paths=_as_path_list(read_only_paths) if read_only_paths is not None else [],
+                backups_dirname=backups_dirname or ".aideon_backups",
+                create_missing_dirs=True if create_missing_dirs is None else bool(create_missing_dirs),
+                atomic_write=True if atomic_write is None else bool(atomic_write),
@@ -53 +84,0 @@ class FileManager:
-            return files or []
@@ -55,5 +86,12 @@ class FileManager:
-            file_path, _ = QFileDialog.getOpenFileName(
-                None,
-                "Выберите файл для анализа",
-                "",
-                "Все файлы (*);;Python Files (*.py)"
+            base = Path(config.base_dir).expanduser().resolve()
+            cfg = FileManagerConfig(
+                base_dir=base,
+                allowed_roots=_as_path_list(allowed_roots) if allowed_roots is not None else (
+                    [Path(p).expanduser().resolve() for p in (config.allowed_roots or [base])]
+                ),
+                read_only_paths=_as_path_list(read_only_paths) if read_only_paths is not None else (
+                    [Path(p).expanduser().resolve() for p in (config.read_only_paths or [])]
+                ),
+                backups_dirname=backups_dirname or config.backups_dirname,
+                create_missing_dirs=config.create_missing_dirs if create_missing_dirs is None else bool(create_missing_dirs),
+                atomic_write=config.atomic_write if atomic_write is None else bool(atomic_write),
@@ -61 +98,0 @@ class FileManager:
-            return [file_path] if file_path else []
@@ -63,6 +100,2 @@ class FileManager:
-    def open_project_dialog(self):
-        """Открывает диалог выбора папки проекта, копирует её в sandbox (с фильтрацией)."""
-        project_path = QFileDialog.getExistingDirectory(None, "Выберите проект для анализа")
-        if not project_path:
-            print("[FileManager] Пользователь отменил выбор проекта.")
-            return None
+        self.cfg = cfg
+        self.base_dir = self._norm(cfg.base_dir)
@@ -70,2 +103,5 @@ class FileManager:
-        project_path = os.path.abspath(project_path)
-        print(f"[FileManager] Исходный проект: {project_path}")
+        # Если allowed_roots не задан — используем только base_dir
+        self.allowed_roots = [self._norm(p) for p in (cfg.allowed_roots or [self.base_dir])]
+        # Гарантируем, что base_dir входит в allowed_roots
+        if not any(str(self.base_dir).startswith(str(r)) or str(r).startswith(str(self.base_dir)) for r in self.allowed_roots):
+            self.allowed_roots.append(self.base_dir)
@@ -73,3 +109,3 @@ class FileManager:
-        if project_path.startswith(self.sandbox_path):
-            print("[FileManager] Предупреждение: проект уже внутри sandbox. Копирование отменено.")
-            return None
+        self.read_only_paths = [self._norm(p) for p in (cfg.read_only_paths or [])]
+        self.backups_dir = self.base_dir / self.cfg.backups_dirname
+        self.backups_dir.mkdir(parents=True, exist_ok=True)
@@ -77,3 +113,2 @@ class FileManager:
-        destination = os.path.join(self.sandbox_path, os.path.basename(project_path))
-        destination = os.path.abspath(destination)
-        print(f"[FileManager] Копируем проект в sandbox: {destination}")
+        log_info(f"[FileManager] base_dir={self.base_dir}")
+        log_info(f"[FileManager] allowed_roots={self.allowed_roots}")
@@ -81,4 +116 @@ class FileManager:
-        # Удаляем старый проект, если есть
-        if os.path.exists(destination):
-            print(f"[FileManager] Удаляем старую копию: {destination}")
-            shutil.rmtree(destination)
+    # ---------- path helpers ----------
@@ -86,2 +118,2 @@ class FileManager:
-        # Запоминаем корневой путь (для _ignore_filter)
-        self._original_project_root = project_path
+    def _norm(self, p: os.PathLike | str) -> Path:
+        return Path(p).expanduser().resolve()
@@ -89,60 +121,7 @@ class FileManager:
-        try:
-            shutil.copytree(
-                src=project_path,
-                dst=destination,
-                ignore=self._ignore_filter  # Используем встроенный ignore
-            )
-            print("[FileManager] Проект скопирован (copytree).")
-        except Exception as e:
-            # Логируем, но всё равно продолжаем (папка может быть частично скопирована)
-            print(f"[FileManager] Ошибка при копировании проекта: {e}")
-            # Можно при желании вернуть None, если считаем операцию провальной
-            # Но если хотим «частично» считать её успешной, не прерываем
-
-        # Сохраняем структуру (того, что успели скопировать)
-        self._save_project_tree(destination)
-        # Запись в history.json
-        self._save_to_history(destination, is_project=True)
-        print("[FileManager] Проект обработан, даже если были ошибки. Возвращаем destination.")
-        return destination
-
-    # ---------------------------------------------------------
-    # Загрузка одиночного файла
-    # ---------------------------------------------------------
-    def save_file(self, source_path):
-        """Копирует файл в sandbox, логирует ошибку, но не прерывает всю работу."""
-        if not source_path:
-            print("[FileManager] save_file: Путь к файлу пуст.")
-            return None
-
-        source_path = os.path.abspath(source_path)
-        filename = os.path.basename(source_path)
-        destination = os.path.join(self.sandbox_path, filename)
-        destination = os.path.abspath(destination)
-
-        print(f"[FileManager] save_file копирование: {source_path} → {destination}")
-
-        try:
-            if self._too_long_path(destination):
-                print(f"[FileManager] Путь слишком длинный: {destination}")
-                return None
-
-            if source_path.startswith(self.sandbox_path):
-                print("[FileManager] Файл уже в sandbox, пропускаем копирование.")
-                return None
-
-            shutil.copy2(source_path, destination)
-            self._save_to_history(destination, is_project=False)
-            print("[FileManager] Файл скопирован в sandbox.")
-            return destination
-        except Exception as e:
-            print(f"[FileManager] Ошибка при копировании файла: {e}")
-            return None
-
-    # ---------------------------------------------------------
-    # Чтение / список / удаление
-    # ---------------------------------------------------------
-    def read_file(self, file_path):
-        if not file_path or not os.path.exists(file_path):
-            print(f"[FileManager] read_file: Файл не найден: {file_path}")
-            return None
+    def _in_allowed_roots(self, p: Path) -> bool:
+        ps = str(p)
+        for root in self.allowed_roots:
+            rs = str(root)
+            if ps == rs or ps.startswith(rs + os.sep) or ps.startswith(rs + "/"):
+                return True
+        return False
@@ -150,18 +129,7 @@ class FileManager:
-        try:
-            with open(file_path, "r", encoding="utf-8") as f:
-                data = f.read()
-            print(f"[FileManager] Файл прочитан: {file_path}")
-            return data
-        except Exception as e:
-            print(f"[FileManager] Ошибка при чтении файла '{file_path}': {e}")
-            return None
-
-    def list_files(self):
-        """Список (файлов и папок) на верхнем уровне sandbox."""
-        try:
-            items = os.listdir(self.sandbox_path)
-            print(f"[FileManager] Содержимое sandbox: {items}")
-            return items
-        except Exception as e:
-            print(f"[FileManager] Ошибка при list_files: {e}")
-            return []
+    def _is_read_only(self, p: Path) -> bool:
+        ps = str(p)
+        for rp in self.read_only_paths:
+            rs = str(rp)
+            if ps == rs or ps.startswith(rs + os.sep) or ps.startswith(rs + "/"):
+                return True
+        return False
@@ -169,4 +137,3 @@ class FileManager:
-    def delete_file(self, filename):
-        """Удаляет файл/папку из sandbox + запись из history. Возвращает bool."""
-        file_path = os.path.join(self.sandbox_path, filename)
-        file_path = os.path.abspath(file_path)
+    def resolve(self, rel_or_abs: os.PathLike | str) -> Path:
+        """
+        Разрешаем путь с учётом allowed_roots.
@@ -174,12 +141,8 @@ class FileManager:
-        if os.path.exists(file_path):
-            print(f"[FileManager] Удаляем: {file_path}")
-            try:
-                if os.path.isdir(file_path):
-                    shutil.rmtree(file_path)
-                else:
-                    os.remove(file_path)
-                self._remove_from_history(file_path)
-                return True
-            except Exception as e:
-                print(f"[FileManager] Ошибка удаления '{file_path}': {e}")
-                return False
+        Правила:
+          - Относительные пути всегда якорим к base_dir.
+          - Абсолютные пути разрешаем, если они лежат в allowed_roots.
+          - Иначе — PermissionError.
+        """
+        raw = Path(rel_or_abs)
+        if not raw.is_absolute():
+            p = self._norm(self.base_dir / raw)
@@ -187,2 +150 @@ class FileManager:
-            print(f"[FileManager] delete_file: Нет такого файла/папки: {file_path}")
-            return False
+            p = self._norm(raw)
@@ -190,19 +152,2 @@ class FileManager:
-    # ---------------------------------------------------------
-    # История (history.json)
-    # ---------------------------------------------------------
-    def _save_to_history(self, path, is_project=False):
-        """Добавляем запись (path, type=file/project) в history.json, если её нет."""
-        history = self._load_history()
-        known_paths = {h["path"] for h in history}
-        if path not in known_paths:
-            entry_type = "project" if is_project else "file"
-            print(f"[FileManager] Добавляем в history: {path} (type={entry_type})")
-            history.append({
-                "path": path,
-                "type": entry_type
-            })
-            try:
-                with open(self.history_path, "w", encoding="utf-8") as f:
-                    json.dump(history, f, indent=4, ensure_ascii=False)
-            except Exception as e:
-                print(f"[FileManager] Ошибка записи history.json: {e}")
+        if not self._in_allowed_roots(p):
+            raise PermissionError(f"Path {p} is outside allowed roots")
@@ -210,3 +155,5 @@ class FileManager:
-    def _load_history(self):
-        if not os.path.exists(self.history_path):
-            return []
+        return p
+
+    # ---------- queries ----------
+
+    def exists(self, path: os.PathLike | str) -> bool:
@@ -214,4 +161,13 @@ class FileManager:
-            with open(self.history_path, "r", encoding="utf-8") as f:
-                return json.load(f)
-        except Exception as e:
-            print(f"[FileManager] Ошибка при чтении history.json: {e}")
+            return self.resolve(path).exists()
+        except Exception:
+            return False
+
+    def is_file(self, path: os.PathLike | str) -> bool:
+        return self.resolve(path).is_file()
+
+    def is_dir(self, path: os.PathLike | str) -> bool:
+        return self.resolve(path).is_dir()
+
+    def list_files(self, root: os.PathLike | str, patterns: Optional[Iterable[str]] = None) -> List[Path]:
+        root_p = self.resolve(root)
+        if not root_p.exists():
@@ -218,0 +175,7 @@ class FileManager:
+        files: List[Path] = []
+        if patterns:
+            for pat in patterns:
+                files.extend(root_p.rglob(pat))
+        else:
+            files = [p for p in root_p.rglob("*") if p.is_file()]
+        return [self._norm(p) for p in files if self._in_allowed_roots(self._norm(p))]
@@ -220,5 +183,27 @@ class FileManager:
-    def _remove_from_history(self, file_path):
-        history = self._load_history()
-        new_hist = [x for x in history if x["path"] != file_path]
-        if len(new_hist) != len(history):
-            print(f"[FileManager] Удаляем из history: {file_path}")
+    # ---------- IO ----------
+
+    def read_text(self, path: os.PathLike | str, encoding: str = "utf-8") -> str:
+        p = self.resolve(path)
+        with p.open("r", encoding=encoding, newline="") as f:
+            return f.read()
+
+    def read_bytes(self, path: os.PathLike | str) -> bytes:
+        p = self.resolve(path)
+        with p.open("rb") as f:
+            return f.read()
+
+    def write_text(self, path: os.PathLike | str, data: str, encoding: str = "utf-8") -> Path:
+        p = self.resolve(path)
+        if self._is_read_only(p):
+            raise PermissionError(f"Path {p} is read-only")
+
+        parent = p.parent
+        if self.cfg.create_missing_dirs:
+            parent.mkdir(parents=True, exist_ok=True)
+
+        # backup старой версии (если была)
+        if p.exists():
+            self._backup_file(p)
+
+        if self.cfg.atomic_write:
+            tmp_fd, tmp_name = tempfile.mkstemp(prefix=".aideon_tmp_", dir=str(parent))
@@ -226,2 +211,3 @@ class FileManager:
-                with open(self.history_path, "w", encoding="utf-8") as f:
-                    json.dump(new_hist, f, indent=4, ensure_ascii=False)
+                with io.open(tmp_fd, "w", encoding=encoding, newline="") as f:
+                    f.write(data)
+                os.replace(tmp_name, p)  # атомарная замена
@@ -229,14 +215,9 @@ class FileManager:
-                print(f"[FileManager] Ошибка записи history.json: {e}")
-
-    # ---------------------------------------------------------
-    # Сохранение структуры проекта (project_tree.json)
-    # ---------------------------------------------------------
-    def _save_project_tree(self, project_path):
-        """Сканируем скопированный проект, записываем структуру в project_tree.json."""
-        project_tree = self.get_project_tree(project_path)
-        print(f"[FileManager] Сохраняем структуру проекта в: {self.project_tree_path}")
-        try:
-            with open(self.project_tree_path, "w", encoding="utf-8") as f:
-                json.dump(project_tree, f, indent=4, ensure_ascii=False)
-        except Exception as e:
-            print(f"[FileManager] Ошибка при сохранении project_tree.json: {e}")
+                try:
+                    os.remove(tmp_name)
+                except Exception:
+                    pass
+                log_error(f"[FileManager] atomic write failed: {e}")
+                raise
+        else:
+            with p.open("w", encoding=encoding, newline="") as f:
+                f.write(data)
@@ -244,12 +225,2 @@ class FileManager:
-    def get_project_tree(self, project_path="app"):
-        """
-        Возвращает структуру каталогов (dict):
-        {
-          ".": [...файлы...],
-          "subdir": [...],
-          ...
-        }
-        Пропускаем нежелательные dirs/files.
-        """
-        project_path = os.path.abspath(project_path)
-        out_tree = {}
+        log_info(f"[FileManager] wrote {p}")
+        return p
@@ -257,3 +228,4 @@ class FileManager:
-        for root, dirs, files in os.walk(project_path):
-            # Фильтруем dirs, чтобы не заходить в EXCLUDED_DIRS
-            dirs[:] = [d for d in dirs if not self._should_skip_dir(d)]
+    def write_bytes(self, path: os.PathLike | str, data: bytes) -> Path:
+        p = self.resolve(path)
+        if self._is_read_only(p):
+            raise PermissionError(f"Path {p} is read-only")
@@ -261,4 +233,3 @@ class FileManager:
-            valid_files = []
-            for f in files:
-                if not self._should_skip_file(f, root_dir=root):
-                    valid_files.append(f)
+        parent = p.parent
+        if self.cfg.create_missing_dirs:
+            parent.mkdir(parents=True, exist_ok=True)
@@ -266,2 +237,2 @@ class FileManager:
-            rel_path = os.path.relpath(root, project_path)
-            out_tree[rel_path] = valid_files
+        if p.exists():
+            self._backup_file(p)
@@ -269 +240,16 @@ class FileManager:
-        return out_tree
+        if self.cfg.atomic_write:
+            tmp_fd, tmp_name = tempfile.mkstemp(prefix=".aideon_tmp_", dir=str(parent))
+            try:
+                with os.fdopen(tmp_fd, "wb") as f:
+                    f.write(data)
+                os.replace(tmp_name, p)
+            except Exception as e:
+                try:
+                    os.remove(tmp_name)
+                except Exception:
+                    pass
+                log_error(f"[FileManager] atomic write (bytes) failed: {e}")
+                raise
+        else:
+            with p.open("wb") as f:
+                f.write(data)
@@ -271,54 +257,4 @@ class FileManager:
-    # ---------------------------------------------------------
-    # Фильтрация (copytree ignore=...) и общие методы
-    # ---------------------------------------------------------
-    def _ignore_filter(self, dir_path, items):
-        """
-        Функция для copytree(ignore=...).
-        Возвращаем список имён, которые надо игнорировать (не копировать).
-        """
-        ignored = []
-
-        # Если не задано, считаем dir_path корнем
-        if not self._original_project_root:
-            self._original_project_root = dir_path
-
-        for name in items:
-            full_path = os.path.join(dir_path, name)
-            rel = os.path.relpath(full_path, self._original_project_root)
-            potential_dest = os.path.join(self.sandbox_path, rel)
-
-            # Проверяем длину пути
-            if self._too_long_path(potential_dest):
-                print(f"[FileManager] Пропускаем '{name}' (слишком длинный путь).")
-                ignored.append(name)
-                continue
-
-            # Проверяем dirs
-            if os.path.isdir(full_path):
-                if self._should_skip_dir(name):
-                    print(f"[FileManager] Пропускаем директорию: '{name}'")
-                    ignored.append(name)
-            else:
-                # Файлы по расширению, размеру
-                if self._should_skip_file(name, root_dir=dir_path):
-                    print(f"[FileManager] Пропускаем файл: '{name}'")
-                    ignored.append(name)
-
-        return ignored
-
-    def _should_skip_dir(self, dirname):
-        return dirname.lower() in EXCLUDED_DIRS
-
-    def _should_skip_file(self, filename, root_dir=None):
-        _, ext = os.path.splitext(filename.lower())
-        if ext in EXCLUDED_EXTS:
-            return True
-
-        if root_dir:
-            full_path = os.path.join(root_dir, filename)
-            if os.path.isfile(full_path):
-                size = os.path.getsize(full_path)
-                if size > MAX_FILE_SIZE:
-                    print(f"[FileManager] _should_skip_file: '{full_path}' (размер {size} > {MAX_FILE_SIZE}).")
-                    return True
-        return False
+        log_info(f"[FileManager] wrote (bytes) {p}")
+        return p
+
+    # ---------- utils ----------
@@ -326,2 +262,41 @@ class FileManager:
-    def _too_long_path(self, path_str):
-        return len(path_str) > MAX_PATH_LENGTH
\ No newline at end of file
+    def ensure_dir(self, path: os.PathLike | str) -> Path:
+        p = self.resolve(path)
+        p.mkdir(parents=True, exist_ok=True)
+        return p
+
+    def copy(self, src: os.PathLike | str, dst: os.PathLike | str) -> None:
+        sp = self.resolve(src)
+        dp = self.resolve(dst)
+        if sp.is_dir():
+            shutil.copytree(sp, dp, dirs_exist_ok=True)
+        else:
+            dp.parent.mkdir(parents=True, exist_ok=True)
+            shutil.copy2(sp, dp)
+
+    def compute_hash(self, path: os.PathLike | str, algo: str = "sha256") -> str:
+        p = self.resolve(path)
+        h = hashlib.new(algo)
+        with p.open("rb") as f:
+            for chunk in iter(lambda: f.read(8192), b""):
+                h.update(chunk)
+        return h.hexdigest()
+
+    def _backup_file(self, path: Path) -> Optional[Path]:
+        # Пытаемся хранить иерархию бэкапов относительно base_dir
+        try:
+            rel = path.relative_to(self.base_dir)
+        except ValueError:
+            rel = Path("_external_") / path.name
+
+        backup_target = self.backups_dir / rel
+        backup_target.parent.mkdir(parents=True, exist_ok=True)
+        shutil.copy2(path, backup_target)
+        log_info(f"[FileManager] backup -> {backup_target}")
+        return backup_target
+
+
+# ============================
+# ✅ Совместимые алиасы/экспорт (строго в конце)
+# ============================
+CoreFileManager = FileManager
+__all__ = ["FileManager", "CoreFileManager", "FileManagerConfig"]
\ No newline at end of file
```

</details>

<details><summary>app/logger.py</summary>

```diff
diff --git a/app/logger.py b/app/logger.py
index efa5e96..0af58b1 100644
--- a/app/logger.py
+++ b/app/logger.py
@@ -0,0 +1,3 @@
+# app/logger.py
+from __future__ import annotations
+
@@ -1,0 +5 @@ import os
+import json
@@ -2,0 +7,2 @@ import logging
+import contextvars
+from typing import Optional
@@ -5,5 +11,4 @@ from logging.handlers import RotatingFileHandler
-# Директория и основные пути
-LOG_DIR = "app/logs"
-os.makedirs(LOG_DIR, exist_ok=True)
-
-MAIN_LOG_FILE = os.path.join(LOG_DIR, "aideon.log")
+# ---------- Константы и пути ----------
+DEFAULT_LOG_DIR = os.getenv("LOG_DIR", "app/logs")
+MAIN_LOG_FILE = "aideon.log"
+AGENT_JSON_FILE = "agent.jsonl"  # новый структурный лог для агента
@@ -11 +16 @@ MAIN_LOG_FILE = os.path.join(LOG_DIR, "aideon.log")
-# Цветной форматтер для консоли
+# ---------- Цветной форматтер для консоли ----------
@@ -22 +27 @@ class ColorFormatter(logging.Formatter):
-    def format(self, record):
+    def format(self, record: logging.LogRecord) -> str:
@@ -24,32 +29,180 @@ class ColorFormatter(logging.Formatter):
-        return f"{color}{super().format(record)}{self.RESET}"
-
-# Форматы
-log_format = "%(asctime)s | %(levelname)s | %(message)s"
-formatter = logging.Formatter(log_format)
-color_formatter = ColorFormatter(log_format)
-
-# Главный логгер
-logger = logging.getLogger("Aideon")
-logger.setLevel(logging.INFO)
-
-# Консольный вывод
-console_handler = logging.StreamHandler()
-console_handler.setFormatter(color_formatter)
-logger.addHandler(console_handler)
-
-# Главный файл логов с ротацией
-file_handler = RotatingFileHandler(MAIN_LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
-file_handler.setFormatter(formatter)
-logger.addHandler(file_handler)
-
-# Отдельные файлы по уровню логов
-for level_name, file_name in [("error", "error.log"), ("warning", "warning.log"), ("info", "info.log")]:
-    handler = logging.FileHandler(os.path.join(LOG_DIR, file_name), encoding="utf-8")
-    handler.setLevel(getattr(logging, level_name.upper()))
-    handler.setFormatter(formatter)
-    logger.addHandler(handler)
-
-# Упрощённые функции
-def log_info(msg): logger.info(msg)
-def log_warning(msg): logger.warning(msg)
-def log_error(msg): logger.error(msg)
\ No newline at end of file
+        base = super().format(record)
+        return f"{color}{base}{self.RESET}"
+
+# ---------- JSON-форматтер для агентских событий ----------
+class JSONFormatter(logging.Formatter):
+    def format(self, record: logging.LogRecord) -> str:
+        base = {
+            "ts": self.formatTime(record, self.datefmt),
+            "level": record.levelname,
+            "msg": record.getMessage(),
+            "logger": record.name,
+        }
+        # контекст агента
+        aid = AGENT_CTX_AGENT_ID.get()
+        rid = AGENT_CTX_RUN_ID.get()
+        tid = AGENT_CTX_TASK_ID.get()
+        if aid is not None:
+            base["agent_id"] = aid
+        if rid is not None:
+            base["run_id"] = rid
+        if tid is not None:
+            base["task_id"] = tid
+
+        # extra (если передали словарь через emit_* )
+        extra_dict = getattr(record, "extra", None)
+        if isinstance(extra_dict, dict):
+            base.update(extra_dict)
+
+        return json.dumps(base, ensure_ascii=False)
+
+# ---------- Контекст агента (contextvars) ----------
+AGENT_CTX_AGENT_ID: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("agent_id", default=None)
+AGENT_CTX_RUN_ID:   contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("run_id",   default=None)
+AGENT_CTX_TASK_ID:  contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("task_id",  default=None)
+
+# ---------- Глобальный синглтон логгера ----------
+_LOGGER: Optional[logging.Logger] = None
+_AGENT_HANDLER_ATTACHED = False  # чтобы не дублировать JSON-хендлер
+
+def _validated_level_from_env() -> tuple[int, str]:
+    level_name = os.getenv("LOG_LEVEL", "INFO").upper().strip()
+    level = getattr(logging, level_name, None)
+    if not isinstance(level, int):
+        # fallback и предупреждение в консоль на этапе первичной инициализации
+        level_name = "INFO"
+        level = logging.INFO
+        print(f"[logger] WARNING: invalid LOG_LEVEL, fallback to INFO")
+    return level, level_name
+
+def setup_logging() -> logging.Logger:
+    """
+    Инициализация логирования:
+      - уровень берём из ENV LOG_LEVEL (DEBUG/INFO/WARNING/ERROR/CRITICAL), по умолчанию INFO
+      - вывод в консоль (цветной)
+      - вывод в файл app/logs/aideon.log (ротация 2MB x 3)
+      - отдельные файлы info.log / warning.log / error.log
+    Повторный вызов безопасен (хендлеры не дублируются).
+    """
+    global _LOGGER
+    if _LOGGER is not None:
+        return _LOGGER
+
+    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
+
+    level, level_name = _validated_level_from_env()
+
+    logger = logging.getLogger("Aideon")
+    logger.setLevel(level)
+    logger.propagate = False  # чтобы не улетало в корневой логгер
+
+    # Форматы
+    fmt = "%(asctime)s | %(levelname)s | %(message)s"
+    datefmt = "%Y-%m-%d %H:%M:%S"
+    text_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
+    color_formatter = ColorFormatter(fmt=fmt, datefmt=datefmt)
+
+    # Проверка на наличие хендлеров — чтобы не дублировать
+    if not logger.handlers:
+        # Консоль (цвет)
+        sh = logging.StreamHandler()
+        sh.setLevel(level)
+        sh.setFormatter(color_formatter)
+        logger.addHandler(sh)
+
+        # Главный файл (ротация)
+        main_path = os.path.join(DEFAULT_LOG_DIR, MAIN_LOG_FILE)
+        fh = RotatingFileHandler(main_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
+        fh.setLevel(level)
+        fh.setFormatter(text_formatter)
+        logger.addHandler(fh)
+
+        # Отдельные файлы по уровням
+        per_level = [
+            (logging.INFO,    "info.log"),
+            (logging.WARNING, "warning.log"),
+            (logging.ERROR,   "error.log"),
+        ]
+        for lvl, fname in per_level:
+            path = os.path.join(DEFAULT_LOG_DIR, fname)
+            h = logging.FileHandler(path, encoding="utf-8")
+            h.setLevel(lvl)
+            h.setFormatter(text_formatter)
+            logger.addHandler(h)
+
+    _LOGGER = logger
+    logger.debug("Логирование инициализировано (level=%s, dir=%s)", level_name, DEFAULT_LOG_DIR)
+    return logger
+
+def _get_logger() -> logging.Logger:
+    return _LOGGER or setup_logging()
+
+# ---------- Агентский JSON-хендлер (лениво подключаем) ----------
+def _ensure_agent_json_handler() -> None:
+    """
+    Добавляет JSON-хендлер в logger один раз.
+    Не трогаем существующие хендлеры → сохраняем совместимость.
+    """
+    global _AGENT_HANDLER_ATTACHED
+    if _AGENT_HANDLER_ATTACHED:
+        return
+    logger = _get_logger()
+    # отдельный файл с JSONL
+    agent_path = os.path.join(DEFAULT_LOG_DIR, AGENT_JSON_FILE)
+    jh = RotatingFileHandler(agent_path, maxBytes=5_000_000, backupCount=5, encoding="utf-8")
+    jh.setLevel(logging.INFO)  # события агента обычно на INFO
+    jh.setFormatter(JSONFormatter(fmt="%(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
+    logger.addHandler(jh)
+    _AGENT_HANDLER_ATTACHED = True
+    logger.debug("Agent JSON handler attached → %s", agent_path)
+
+# ---------- Контекст и события агента ----------
+def set_agent_context(agent_id: str | None = None, run_id: str | None = None, task_id: str | None = None) -> None:
+    """
+    Устанавливает контекст для JSON-событий агента.
+    Безопасно вызывать много раз (значения можно обновлять/сбрасывать).
+    """
+    if agent_id is not None:
+        AGENT_CTX_AGENT_ID.set(agent_id)
+    if run_id is not None:
+        AGENT_CTX_RUN_ID.set(run_id)
+    if task_id is not None:
+        AGENT_CTX_TASK_ID.set(task_id)
+
+def emit_event(event: str, **fields) -> None:
+    """
+    Универсальная точка эмиссии JSON-событий.
+    Пишет в отдельный agent.jsonl и в обычные текстовые логи (через info).
+    """
+    _ensure_agent_json_handler()
+    logger = _get_logger()
+    # кладём payload в record.extra, JSONFormatter его подхватит
+    logger.info(event, extra={"extra": {"event": event, **fields}})
+
+def emit_tool_call(tool: str, action: str, latency_ms: int | None = None, **fields) -> None:
+    emit_event("tool_call", tool=tool, action=action, latency_ms=latency_ms, **fields)
+
+def emit_plan_started(goal: str, **fields) -> None:
+    emit_event("plan_started", goal=goal, **fields)
+
+def emit_action(step: str, status: str = "started", **fields) -> None:
+    emit_event("action", step=step, status=status, **fields)
+
+def emit_plan_finished(result: str, **fields) -> None:
+    emit_event("plan_finished", result=result, **fields)
+
+def emit_agent_error(err: str, **fields) -> None:
+    emit_event("error", error=err, **fields)
+
+# ---------- Упрощённые функции (совместимость с существующим кодом) ----------
+def log_debug(msg: str) -> None:
+    _get_logger().debug(msg)
+
+def log_info(msg: str) -> None:
+    _get_logger().info(msg)
+
+def log_warning(msg: str) -> None:
+    _get_logger().warning(msg)
+
+def log_error(msg: str) -> None:
+    _get_logger().error(msg)
\ No newline at end of file
```

</details>

<details><summary>"app/logger\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"</summary>

_No textual diff (binary or rename)._

</details>

<details><summary>app/modules/analyzer.py</summary>

```diff
diff --git a/app/modules/analyzer.py b/app/modules/analyzer.py
index 82d6e79..e57dd4d 100644
--- a/app/modules/analyzer.py
+++ b/app/modules/analyzer.py
@@ -5 +4,0 @@ import json
-import os
@@ -10 +9 @@ from app.core.file_manager import FileManager
-from app.utils import load_api_key  # тянет ключ из ENV/.env/settings, ключи НЕ храним в репо
+from app.modules.utils import load_api_key, load_model_name, load_temperature
@@ -12 +11 @@ from app.utils import load_api_key  # тянет ключ из ENV/.env/settings
-# Пытаемся использовать новый клиент OpenAI, иначе fallback на старый openai.*
+# Новый SDK (openai>=1.x)
@@ -14 +13 @@ try:
-    from openai import OpenAI  # новый SDK (openai>=1.x)
+    from openai import OpenAI
@@ -19 +18 @@ except Exception:
-# Старый SDK (openai<1.x)
+# Старый SDK (openai<1.x) — совместимость
@@ -22 +21 @@ try:
-except Exception:  # pragma: no cover
+except Exception:
@@ -28,4 +27,4 @@ class CodeAnalyzer:
-    Модуль анализа/генерации кода через OpenAI.
-    - Ключ берём из ENV/.env (см. load_api_key)
-    - Имя модели: ENV OPENAI_MODEL > config["openai"]["model_name"] > config["model_name"] > "gpt-4o"
-    - Поддержка нового и старого SDK, ретраи/таймауты.
+    Анализ и генерация кода через OpenAI.
+    - Ключ берём через load_api_key
+    - Имя модели: ENV > config > "gpt-4o"
+    - Поддержка нового и старого SDK
@@ -39,2 +38,2 @@ class CodeAnalyzer:
-        self.openai_model = self._resolve_model_name(self.config)
-        self.temperature = float(self.config.get("temperature", 0.7))
+        self.openai_model = load_model_name(self.config) or "gpt-4o"
+        self.temperature = load_temperature(self.config)
@@ -45 +44 @@ class CodeAnalyzer:
-        # Новый клиент, если доступен
+        # Клиент нового SDK (если доступен)
@@ -53 +52 @@ class CodeAnalyzer:
-        print("✅ Используется ChatGPT (OpenAI).")
+        print(f"✅ Используется OpenAI. Модель: {self.openai_model}")
@@ -58,3 +56,0 @@ class CodeAnalyzer:
-        """
-        Свободный диалог с ChatGPT.
-        """
@@ -68,4 +63,0 @@ class CodeAnalyzer:
-        """
-        Анализ кода (через OpenAI) с поддержкой chunk-обработки для больших файлов.
-        Возвращает JSON-строку.
-        """
@@ -76,4 +68 @@ class CodeAnalyzer:
-        combined: Dict[str, str] = {
-            "chat": "", "problems": "", "plan": "",
-            "process": "", "result": "", "code": ""
-        }
+        combined: Dict[str, str] = {k: "" for k in ["chat", "problems", "plan", "process", "result", "code"]}
@@ -95 +84 @@ class CodeAnalyzer:
-    # ---------- Внутренние вспомогательные ----------
+    # ---------- Внутренние методы ----------
@@ -98,3 +86,0 @@ class CodeAnalyzer:
-        """
-        Запрос к OpenAI для анализа отдельного чанка кода.
-        """
@@ -104,2 +90,2 @@ class CodeAnalyzer:
-            f"Тебе дана структура проекта:\n{project_tree}\n\n"
-            f"Анализируй следующий код:\n{code_chunk}\n\n"
+            f"Структура проекта:\n{project_tree}\n\n"
+            f"Анализируй код:\n{code_chunk}\n\n"
@@ -115 +101 @@ class CodeAnalyzer:
-            "Не добавляй ничего, кроме JSON."
+            "Без пояснений вне JSON."
@@ -125,7 +111 @@ class CodeAnalyzer:
-        """
-        Заглушка: локальные модели отключены.
-        """
-        return (
-            "❌ Локальная модель StarCoder временно отключена. "
-            "Используйте ChatGPT для генерации кода."
-        )
+        return "❌ Локальные модели отключены. Используйте OpenAI."
@@ -134,5 +114,2 @@ class CodeAnalyzer:
-        """
-        Грубое разбиение текста по количеству слов ~ контексту.
-        """
-        text = text.strip()
-        if not text:
+        words = text.strip().split()
+        if not words:
@@ -140,2 +116,0 @@ class CodeAnalyzer:
-
-        words = text.split()
@@ -143 +118,2 @@ class CodeAnalyzer:
-            return [text]
+            return [" ".join(words)]
+        return [" ".join(words[i:i + max_ctx]) for i in range(0, len(words), max_ctx)]
@@ -145,4 +121 @@ class CodeAnalyzer:
-        chunks: List[str] = []
-        for i in range(0, len(words), max_ctx):
-            chunks.append(" ".join(words[i:i + max_ctx]))
-        return chunks
+    # ---------- Единая точка вызова OpenAI (без Responses API) ----------
@@ -150,15 +122,0 @@ class CodeAnalyzer:
-    def _resolve_model_name(self, cfg: Dict[str, Any]) -> str:
-        """
-        Приоритет: ENV OPENAI_MODEL > cfg['openai']['model_name'] > cfg['model_name'] > 'gpt-4o'
-        """
-        env_model = os.getenv("OPENAI_MODEL")
-        if env_model:
-            return env_model
-        openai_cfg = cfg.get("openai")
-        if isinstance(openai_cfg, dict) and openai_cfg.get("model_name"):
-            return str(openai_cfg["model_name"])
-        if cfg.get("model_name"):
-            return str(cfg["model_name"])
-        return "gpt-4o"
-
-    # --- Приватный унифицированный вызов OpenAI с ретраями/таймаутами ---
@@ -167,2 +125,2 @@ class CodeAnalyzer:
-        Единая точка вызова OpenAI (новый клиент или fallback на старый API).
-        Ретраи с экспоненциальной паузой. Возвращает строку-ответ или сообщение об ошибке.
+        Стабильный путь: только chat.completions (новый SDK) + фолбэк на старый SDK.
+        Убрали Responses API, чтобы не ловить 400 'messages[...].content[0].type'.
@@ -174,40 +132,11 @@ class CodeAnalyzer:
-                # Новый SDK?
-                if self._client is not None:
-                    # 1) сначала пробуем Responses API (современнее)
-                    if hasattr(self._client, "responses"):
-                        try:
-                            resp = self._client.responses.create(
-                                model=self.openai_model,
-                                input=messages,  # roles поддерживаются в новом API
-                                temperature=self.temperature,
-                                timeout=self.request_timeout,
-                            )
-                            # Вытаскиваем текст из первого message.content[0].text
-                            if resp and resp.output and len(resp.output) > 0:
-                                # Унификация: у разных версий поля отличаются; берём безопасно
-                                first = resp.output[0]
-                                # some SDKs: first.content[0].text
-                                text = None
-                                try:
-                                    if hasattr(first, "content") and first.content:
-                                        seg = first.content[0]
-                                        text = getattr(seg, "text", None) or getattr(seg, "content", None)
-                                except Exception:
-                                    text = None
-                                if isinstance(text, str) and text.strip():
-                                    return text.strip()
-                        except Exception as e_resp:
-                            # Если responses не сработал — пробуем chat.completions
-                            last_err = e_resp
-
-                    # 2) chat.completions (совместимость)
-                    if hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
-                        resp2 = self._client.chat.completions.create(
-                            model=self.openai_model,
-                            messages=messages,
-                            temperature=self.temperature,
-                            timeout=self.request_timeout,
-                        )
-                        return (resp2.choices[0].message.content or "").strip()
-
-                # Старый SDK
+                # Новый SDK (рекомендуемый путь)
+                if self._client is not None and hasattr(self._client, "chat") and hasattr(self._client.chat, "completions"):
+                    resp = self._client.chat.completions.create(
+                        model=self.openai_model,
+                        messages=messages,
+                        temperature=self.temperature,
+                        timeout=self.request_timeout,
+                    )
+                    return (resp.choices[0].message.content or "").strip()
+
+                # Старый SDK — совместимость
@@ -224,2 +153 @@ class CodeAnalyzer:
-                # Если ни один путь не сработал
-                return "Ошибка: OpenAI SDK не инициализирован."
+                return "Ошибка: OpenAI SDK не найден."
@@ -229,3 +157,6 @@ class CodeAnalyzer:
-                # Специальная обработка 401 (неверный ключ)
-                err_str = str(e)
-                if "401" in err_str or "invalid_api_key" in err_str or "Incorrect API key" in err_str:
+                err_txt = str(e)
+
+                # Частые случаи — отдельные подсказки
+                if "401" in err_txt or "invalid_api_key" in err_txt or "Incorrect API key" in err_txt:
+                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
+                if "missing required parameter" in err_txt.lower() and "messages" in err_txt.lower():
@@ -233,2 +164,2 @@ class CodeAnalyzer:
-                        "Ошибка при обращении к OpenAI: неверный API-ключ (401). "
-                        "Проверьте OPENAI_API_KEY в .env/окружении."
+                        "Ошибка: некорректный формат запроса для модели (400). "
+                        "Проверьте формирование сообщений (role/content)."
@@ -235,0 +167 @@ class CodeAnalyzer:
+
```

</details>

<details><summary>app/modules/fixer.py</summary>

```diff
diff --git a/app/modules/fixer.py b/app/modules/fixer.py
index ec89bfa..bf829b5 100644
--- a/app/modules/fixer.py
+++ b/app/modules/fixer.py
@@ -0,0 +1 @@
+# app/modules/fixer.py
@@ -3,0 +5,5 @@
+Совместим с новым SDK OpenAI (>=1.x) и имеет фолбэк на старый.
+
+Актуализации:
+- Переведён на новый интерфейс CodePatcher (apply_patch_no_prompt без save_only/interactive_confirm).
+- Добавлены безопасные вызовы агентских событий (emit_*), если доступны в app.logger.
@@ -6 +12,2 @@
-import openai
+from __future__ import annotations
+
@@ -8 +14,0 @@ import difflib
-import os
@@ -10 +16,3 @@ import json
-from app.utils import load_api_key
+import os
+from typing import Any, Dict, Optional
+
@@ -12,0 +21,38 @@ from app.modules.runner import CodeRunner
+from app.modules.improver.patcher import CodePatcher
+from app.modules.utils import load_api_key, load_model_name, load_temperature
+from app.logger import log_info, log_warning, log_error
+
+# Опциональные агентские события (если в logger есть расширения — используем; иначе — no-op)
+try:
+    from app.logger import (
+        set_agent_context,
+        emit_event,
+        emit_tool_call,
+        emit_agent_error,
+        emit_action,
+    )
+except Exception:  # мягкий фолбэк — никакого падения, просто пустые функции
+    def set_agent_context(*args, **kwargs):  # type: ignore
+        return None
+    def emit_event(*args, **kwargs):  # type: ignore
+        return None
+    def emit_tool_call(*args, **kwargs):  # type: ignore
+        return None
+    def emit_agent_error(*args, **kwargs):  # type: ignore
+        return None
+    def emit_action(*args, **kwargs):  # type: ignore
+        return None
+
+# Новый SDK (openai>=1.x)
+try:
+    from openai import OpenAI
+    _HAS_OAI_CLIENT = True
+except Exception:
+    _HAS_OAI_CLIENT = False
+
+# Старый SDK (openai<1.x)
+try:
+    import openai  # type: ignore
+except Exception:
+    openai = None  # type: ignore
+
@@ -15 +61 @@ class CodeFixer:
-    def __init__(self, config):
+    def __init__(self, config: Optional[Dict[str, Any]] = None):
@@ -16,0 +63,2 @@ class CodeFixer:
+
+        # Конфиг/ENV
@@ -18 +66,4 @@ class CodeFixer:
-        self.model = self.config.get("model_name", "gpt-4-turbo")
+        self.model = load_model_name(self.config) or "gpt-4o"
+        self.temperature = load_temperature(self.config)
+
+        # Инструменты
@@ -21 +72,15 @@ class CodeFixer:
-        self.history_path = "app/logs/history.json"  # Файл истории изменений
+        # единая точка бэкапа/диффа/записи (совместимо с актуальной версией)
+        self.patcher = CodePatcher()
+
+        # История
+        self.history_path = os.path.join("app", "logs", "history.json")
+        os.makedirs(os.path.dirname(self.history_path), exist_ok=True)
+
+        # OpenAI client (новый SDK)
+        self._client: Optional["OpenAI"] = None
+        if _HAS_OAI_CLIENT:
+            try:
+                self._client = OpenAI(api_key=self.api_key)
+            except Exception as e:
+                log_warning(f"[CodeFixer] Не удалось инициализировать OpenAI client: {e}")
+                self._client = None
@@ -23 +88,12 @@ class CodeFixer:
-    def suggest_fixes(self, code_text, file_path=None):
+        # Агентский контекст (если включён в логгере)
+        set_agent_context(
+            agent_id=self.config.get("agent_id", "aideon-fixer"),
+            run_id=self.config.get("run_id", None),
+            task_id=self.config.get("task_id", None),
+        )
+
+        log_info(f"[CodeFixer] ✅ Инициализирован. Модель={self.model}, temp={self.temperature}")
+
+    # ---------- GPT ----------
+
+    def _chat(self, messages: list[dict[str, str]]) -> str:
@@ -25 +101,3 @@ class CodeFixer:
-        Запрос к GPT, чтобы предложить исправления/рефакторинг кода.
+        Унифицированный вызов чата:
+        - сначала пытаемся новый SDK (chat.completions),
+        - затем — старый SDK (ChatCompletion).
@@ -27 +105,39 @@ class CodeFixer:
-        openai.api_key = self.api_key
+        # Новый SDK
+        if self._client is not None:
+            try:
+                emit_action(step="fixer_chat", status="started", provider="openai", sdk=">=1.x")
+                resp = self._client.chat.completions.create(
+                    model=self.model,
+                    messages=messages,
+                    temperature=self.temperature,
+                )
+                out = (resp.choices[0].message.content or "").strip()
+                emit_action(step="fixer_chat", status="done", chars=len(out))
+                return out
+            except Exception as e:
+                # Если 401/invalid key — возвращаем понятное сообщение
+                msg = str(e)
+                if "401" in msg or "invalid_api_key" in msg or "Incorrect API key" in msg:
+                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
+                log_warning(f"[CodeFixer] Ошибка нового SDK: {e}")
+                emit_agent_error("fixer_chat_newsdk_error", error=str(e))
+
+        # Старый SDK
+        if openai is not None:
+            try:
+                emit_action(step="fixer_chat", status="started", provider="openai", sdk="<1.x")
+                openai.api_key = self.api_key
+                resp = openai.ChatCompletion.create(
+                    model=self.model,
+                    messages=messages,
+                    temperature=self.temperature,
+                )
+                out = (resp["choices"][0]["message"]["content"] or "").strip()
+                emit_action(step="fixer_chat", status="done", chars=len(out))
+                return out
+            except Exception as e2:
+                msg = str(e2)
+                if "401" in msg or "invalid_api_key" in msg or "Incorrect API key" in msg:
+                    return "Ошибка: неверный API-ключ (401). Проверьте OPENAI_API_KEY."
+                emit_agent_error("fixer_chat_oldsdk_error", error=str(e2))
+                return f"Ошибка при обращении к AI: {e2}"
@@ -29 +145,9 @@ class CodeFixer:
-        # Получаем структуру проекта
+        return "Ошибка: OpenAI SDK не найден."
+
+    # ---------- Публичные методы ----------
+
+    def suggest_fixes(self, code_text: str, file_path: Optional[str] = None) -> str:
+        """
+        Запрос к GPT, чтобы предложить исправления/рефакторинг кода.
+        Возвращает СЫРОЙ текст (ожидается JSON по протоколу подсказки).
+        """
@@ -32,2 +156 @@ class CodeFixer:
-        # Формируем полный контекст
-        prompt = (
+        system_prompt = (
@@ -35 +158 @@ class CodeFixer:
-            "Тебе дана структура проекта:\n\n"
+            "Тебе дана структура проекта (вырезка):\n\n"
@@ -37,3 +160 @@ class CodeFixer:
-            "Теперь исправь следующий код:\n"
-            f"{code_text}\n\n"
-            "Ответ должен быть в JSON формате с ключами:\n"
+            "Работай строго по формату JSON:\n"
@@ -41,5 +162,5 @@ class CodeFixer:
-            "  \"chat\": \"...\",  // Ответ в чате\n"
-            "  \"problems\": \"...\",  // Найденные проблемы\n"
-            "  \"plan\": \"...\",  // Пошаговый план исправления\n"
-            "  \"code\": \"...\",  // Исправленный код\n"
-            "  \"diff\": \"...\"  // Разница между старым и новым кодом\n"
+            '  "chat": "...",\n'
+            '  "problems": "...",\n'
+            '  "plan": "...",\n'
+            '  "code": "...",\n'
+            '  "diff": "..." \n'
@@ -47 +168 @@ class CodeFixer:
-            "Не добавляй ничего, кроме JSON."
+            "Никакого текста вне JSON."
@@ -50,9 +171,5 @@ class CodeFixer:
-        try:
-            response = openai.ChatCompletion.create(
-                model=self.model,
-                messages=[
-                    {"role": "system", "content": prompt},
-                    {"role": "user", "content": f"Исправь код в файле {file_path or 'без имени'}:\n{code_text}"}
-                ],
-                temperature=0.7
-            )
+        user_prompt = (
+            f"Исправь код в файле {file_path or 'без имени'}:\n"
+            f"{code_text}\n\n"
+            "Верни строго JSON по указанной схеме."
+        )
@@ -60 +177,4 @@ class CodeFixer:
-            return response["choices"][0]["message"]["content"]
+        messages = [
+            {"role": "system", "content": system_prompt},
+            {"role": "user",   "content": user_prompt},
+        ]
@@ -62,2 +182,6 @@ class CodeFixer:
-        except Exception as e:
-            return f"Ошибка при обращении к AI: {e}"
+        log_info("[CodeFixer] 🤖 Запрос AI на предложение исправлений…")
+        emit_event("fixer_suggest_start", file=file_path or "unknown")
+        result = self._chat(messages)
+        emit_event("fixer_suggest_done", file=file_path or "unknown", length=len(result or ""))
+        log_info(f"[CodeFixer] 📨 Ответ от AI получен ({len(result)} симв.)")
+        return result
@@ -65 +189 @@ class CodeFixer:
-    def apply_fixes(self, original_code, fixed_code, file_path):
+    def apply_fixes(self, original_code: str, fixed_code: str, file_path: str) -> str:
@@ -67 +191,3 @@ class CodeFixer:
-        Применяет исправления, записывая новый код в файл.
+        Применяет исправления:
+        - бэкап/дифф/запись — через CodePatcher.apply_patch_no_prompt(...)
+        - затем запускает тесты; при ошибке — откат бэкапа выполняется тут же вручную
@@ -69,3 +194,0 @@ class CodeFixer:
-        backup_path = f"{file_path}.backup"
-
-        # Создаём бэкап перед изменением
@@ -73,2 +196,10 @@ class CodeFixer:
-            with open(file_path, "r", encoding="utf-8") as original, open(backup_path, "w", encoding="utf-8") as backup:
-                backup.write(original.read())
+            # Новый актуальный интерфейс: создаём бэкап, сохраняем diff и перезаписываем файл
+            self.patcher.apply_patch_no_prompt(
+                file_path=file_path,
+                old_code=original_code,
+                new_code=fixed_code,
+                save_backup=True,   # делаем бэкап
+                save_diff=True,     # сохраняем diff
+            )
+            emit_tool_call("patcher", "apply_patch_no_prompt", file=file_path, mode="write")
+            log_info(f"[CodeFixer] ✅ Патч применён: {file_path}")
@@ -76 +207,3 @@ class CodeFixer:
-            return f"Ошибка при создании резервной копии: {e}"
+            log_error(f"[CodeFixer] ❌ Ошибка при применении патча: {e}")
+            emit_agent_error("fixer_apply_patch_error", file=file_path, error=str(e))
+            return f"Ошибка при записи исправленного кода: {e}"
@@ -77,0 +211 @@ class CodeFixer:
+        # Сгенерируем diff для отчёта (дополнительно к сохранённому в patches/)
@@ -80,9 +214,2 @@ class CodeFixer:
-        try:
-            with open(file_path, "w", encoding="utf-8") as f:
-                f.write(fixed_code)
-
-            # Запускаем тест после исправления
-            return self.run_tests(file_path, diff, fixed_code)
-
-        except Exception as e:
-            return f"Ошибка при записи исправленного кода: {e}"
+        # Запуск проверки/тестов
+        return self.run_tests(file_path, diff, fixed_code)
@@ -90 +217 @@ class CodeFixer:
-    def generate_diff(self, original_code, fixed_code):
+    def generate_diff(self, original_code: str, fixed_code: str) -> str:
@@ -92 +219 @@ class CodeFixer:
-        Генерирует diff между старым и новым кодом.
+        Генерирует unified diff между старым и новым кодом.
@@ -97 +224,3 @@ class CodeFixer:
-        diff = difflib.unified_diff(original_lines, fixed_lines, lineterm="")
+        diff = difflib.unified_diff(
+            original_lines, fixed_lines, fromfile="original", tofile="fixed", lineterm=""
+        )
@@ -100 +229 @@ class CodeFixer:
-    def run_tests(self, file_path, diff, fixed_code):
+    def run_tests(self, file_path: str, diff: str, fixed_code: str) -> str:
@@ -102,2 +231,3 @@ class CodeFixer:
-        Запускает тестирование кода после исправления.
-        Если тесты не проходят, откатываемся к бэкапу и записываем это в историю.
+        Запускает выполнение файла после исправления.
+        Если выполнение завершилось с ошибкой — пытается откатиться к бэкапу
+        (бэкап делал CodePatcher перед записью).
@@ -105,0 +236,3 @@ class CodeFixer:
+        log_info(f"[CodeFixer] 🧪 Запуск проверки файла: {file_name}")
+        emit_action(step="fixer_run", status="started", file=file_name)
+
@@ -114 +247 @@ class CodeFixer:
-            "status": "Успешно" if return_code == 0 else "Ошибка"
+            "status": "Успешно" if return_code == 0 else "Ошибка",
@@ -116,2 +248,0 @@ class CodeFixer:
-
-        # Записываем историю исправлений
@@ -121,6 +252,20 @@ class CodeFixer:
-            return f"Исправления успешно применены и протестированы:\n{diff}\nВывод тестов:\n{stdout}"
-        else:
-            # Откатываем изменения, если тесты не прошли
-            backup_path = f"{file_path}.backup"
-            if os.path.exists(backup_path):
-                os.replace(backup_path, file_path)
+            emit_action(step="fixer_run", status="done", file=file_name, result="ok")
+            log_info("[CodeFixer] ✅ Исправления применены и проверка прошла успешно")
+            return f"Исправления успешно применены и протестированы:\n{diff}\nВывод:\n{stdout}"
+
+        # Ошибка — попробуем откатиться (бэкап создавал патчер)
+        log_warning("[CodeFixer] ❌ Ошибка при проверке — попытка отката к бэкапу")
+        emit_action(step="fixer_run", status="done", file=file_name, result="error")
+
+        backup_dir = self.patcher.backup_dir
+        base = os.path.basename(file_path)
+        try:
+            cand = [
+                f for f in os.listdir(backup_dir)
+                if f.startswith(base + ".") and f.endswith(".bak")
+            ]
+            cand.sort(reverse=True)
+            if cand:
+                latest = os.path.join(backup_dir, cand[0])
+                with open(latest, "r", encoding="utf-8") as bf, open(file_path, "w", encoding="utf-8") as wf:
+                    wf.write(bf.read())
@@ -129 +274,3 @@ class CodeFixer:
-                return f"Ошибка во время тестирования! Код откатился к предыдущей версии.\n{stderr}"
+                log_warning(f"[CodeFixer] ↩️ Откат выполнен из бэкапа: {latest}")
+                emit_event("fixer_rollback_done", file=file_name, backup=latest)
+                return f"Ошибка во время проверки! Код откатился к предыдущей версии.\n{stderr}"
@@ -131 +278,9 @@ class CodeFixer:
-                return f"Ошибка во время тестирования, но резервной копии нет!\n{stderr}"
+                log_error("[CodeFixer] Бэкап не найден — откат невозможен")
+                emit_agent_error("fixer_rollback_missing_backup", file=file_name)
+                return f"Ошибка во время тестирования, и резервной копии не найдено!\n{stderr}"
+        except Exception as e:
+            log_error(f"[CodeFixer] Ошибка при откате: {e}")
+            emit_agent_error("fixer_rollback_error", file=file_name, error=str(e))
+            return f"Ошибка во время тестирования и при откате: {e}\n{stderr}"
+
+    # ---------- История ----------
@@ -133 +288 @@ class CodeFixer:
-    def _save_to_history(self, entry):
+    def _save_to_history(self, entry: Dict[str, Any]) -> None:
@@ -135 +290 @@ class CodeFixer:
-        Сохраняет информацию об исправлении в history.json.
+        Сохраняет информацию об исправлении в history.json (без падений на битом файле).
@@ -138,0 +294,5 @@ class CodeFixer:
+        try:
+            with open(self.history_path, "w", encoding="utf-8") as f:
+                json.dump(history, f, indent=2, ensure_ascii=False)
+        except Exception as e:
+            log_warning(f"[CodeFixer] Не удалось записать историю: {e}")
@@ -140,4 +300 @@ class CodeFixer:
-        with open(self.history_path, "w", encoding="utf-8") as f:
-            json.dump(history, f, indent=4, ensure_ascii=False)
-
-    def _load_history(self):
+    def _load_history(self) -> list[Dict[str, Any]]:
@@ -145 +302 @@ class CodeFixer:
-        Загружает историю исправлений.
+        Загружает историю исправлений, возвращает [] при любой ошибке.
@@ -149,2 +306,6 @@ class CodeFixer:
-        with open(self.history_path, "r", encoding="utf-8") as f:
-            return json.load(f)
\ No newline at end of file
+        try:
+            with open(self.history_path, "r", encoding="utf-8") as f:
+                data = json.load(f)
+            return data if isinstance(data, list) else []
+        except Exception:
+            return []
\ No newline at end of file
```

</details>

<details><summary>app/modules/improver/ai_bug_fixer.py</summary>

```diff
diff --git a/app/modules/improver/ai_bug_fixer.py b/app/modules/improver/ai_bug_fixer.py
new file mode 100644
index 0000000..960cfe8
--- /dev/null
+++ b/app/modules/improver/ai_bug_fixer.py
@@ -0,0 +1,163 @@
+# app/modules/improver/ai_bug_fixer.py
+from __future__ import annotations
+
+from typing import Optional, Any, Callable
+import time
+
+from app.modules.analyzer import CodeAnalyzer
+from app.logger import log_info, log_warning, log_error
+
+# Опциональные агентские события (если расширения есть в logger — используем; иначе no-op)
+try:
+    from app.logger import (
+        emit_event,
+        emit_action,
+        emit_agent_error,
+    )
+except Exception:
+    def emit_event(*args, **kwargs):  # type: ignore
+        return None
+    def emit_action(*args, **kwargs):  # type: ignore
+        return None
+    def emit_agent_error(*args, **kwargs):  # type: ignore
+        return None
+
+
+def _strip_fences(text: str) -> str:
+    """
+    Убирает возможные ограждения кодом вида:
+    ```python ... ``` или ``` ... ```
+    без разрушения содержимого.
+    """
+    if not text:
+        return text
+    s = text.strip()
+    if s.startswith("```"):
+        # удалим начальный ```
+        s = s[3:].lstrip()
+        # если сразу идёт идентификатор языка — отрежем его до конца строки
+        nl = s.find("\n")
+        if nl != -1:
+            s = s[nl + 1 :]
+        else:
+            # строка вида "```python" без переноса — возвращаем пусто
+            return ""
+        # убрать возможный завершающий ```
+        if s.endswith("```"):
+            s = s[: -3].rstrip()
+    return s
+
+
+class AIBugFixer:
+    """
+    Мини-модуль «AI-Assisted Bug Fixer».
+
+    Задачи:
+      1) На основе summary + кода попросить у GPT выявить вероятные баги и дать краткий план фикса.
+      2) Запросить у GPT «новую версию файла» (полный текст), вернуть как строку без Markdown-ограждений.
+      3) При ошибке применения — сделать до N повторов (итеративный цикл).
+
+    Модуль НЕ работает с файловой системой напрямую — все действия записи выполняются внешними колбэками.
+    """
+
+    def __init__(self, analyzer: CodeAnalyzer, max_fix_cycles: int = 2):
+        self.analyzer = analyzer
+        self.max_fix_cycles = int(max_fix_cycles)
+
+    # ---------- Промпты ----------
+
+    def propose_fixes(self, file_path: str, summary: Any, code: str) -> str:
+        """
+        Просим у модели кратко описать потенциальные ошибки и план исправления (3–7 пунктов).
+        Возвращает человекочитаемый текст (для логов/истории).
+        """
+        system_msg = "Ты — строгий и практичный ревьюер кода. Отвечай кратко и по делу."
+        user_prompt = (
+            "Тебе дан файл и его summary.\n\n"
+            f"Файл: {file_path}\n"
+            f"Summary:\n{summary}\n\n"
+            "Код:\n"
+            f"{code}\n\n"
+            "Определи вероятные ошибки, точки риска и дай краткий план исправления "
+            "(маркдаун-список, 3–7 пунктов). Если критичных ошибок нет, напиши 'Нет явных ошибок'."
+        )
+        try:
+            emit_action(step="bugfixer_plan", status="started", file=file_path)
+            plan = self.analyzer.chat(user_prompt, system_msg=system_msg)
+            plan = (plan or "").strip() or "Нет ответа от модели"
+            emit_action(step="bugfixer_plan", status="done", file=file_path, chars=len(plan))
+            return plan
+        except Exception as e:
+            log_warning(f"[BugFixer] Не удалось получить план фиксов: {e}")
+            emit_agent_error("bugfixer_plan_error", file=file_path, error=str(e))
+            return f"Ошибка: {e}"
+
+    def generate_fixed_code(self, file_path: str, summary: Any, code: str) -> Optional[str]:
+        """
+        Просим у модели вернуть ПОЛНУЮ обновлённую версию файла (единым текстом),
+        без Markdown-разметки и комментариев вне кода.
+        """
+        system_msg = "Ты — опытный Python-разработчик. Верни только код файла, без Markdown."
+        user_prompt = (
+            "Верни ПОЛНУЮ обновлённую версию файла (единым текстом), исправив ошибки и повысив устойчивость.\n"
+            "Не добавляй подсветку/форматирование/разметку — только чистый код.\n\n"
+            f"Файл: {file_path}\n"
+            f"Summary:\n{summary}\n\n"
+            "Текущая версия:\n"
+            f"{code}\n\n"
+            "Требования:\n"
+            "- Сохрани публичные API и совместимость с текущей логикой.\n"
+            "- Не ломай зависимости проекта.\n"
+            "- При сомнениях оставь краткий TODO-комментарий в коде.\n"
+        )
+        try:
+            emit_action(step="bugfixer_generate", status="started", file=file_path)
+            new_code = self.analyzer.chat(user_prompt, system_msg=system_msg)
+            if not new_code:
+                emit_action(step="bugfixer_generate", status="done", file=file_path, result="empty")
+                return None
+            stripped = _strip_fences(new_code)
+            emit_action(step="bugfixer_generate", status="done", file=file_path, chars=len(stripped))
+            return stripped
+        except Exception as e:
+            log_error(f"[BugFixer] Ошибка при запросе фикса: {e}")
+            emit_agent_error("bugfixer_generate_error", file=file_path, error=str(e))
+            return None
+
+    # ---------- Итеративный цикл ----------
+
+    def iterative_fix_cycle(
+        self,
+        file_path: str,
+        summary: Any,
+        old_code: str,
+        apply_callback: Callable[[str], None],   # обязан применить патч/сохранить diff/и т.п. (может бросить исключение)
+        on_error_callback: Callable[[Exception, int], None],  # уведомление о фейле применения
+    ) -> Optional[str]:
+        """
+        Делает до N попыток получить и применить исправленный код.
+        Возвращает применённый код (str) на успехе или None на неудаче.
+        """
+        for attempt in range(1, self.max_fix_cycles + 1):
+            emit_event("bugfixer_attempt", file=file_path, attempt=attempt, total=self.max_fix_cycles)
+
+            plan = self.propose_fixes(file_path, summary, old_code)
+            log_info(f"[BugFixer] План фиксов (попытка {attempt}/{self.max_fix_cycles}):\n{plan}")
+
+            new_code = self.generate_fixed_code(file_path, summary, old_code)
+            if not new_code:
+                log_warning("[BugFixer] Модель не вернула новую версию кода.")
+                on_error_callback(RuntimeError("Модель не вернула код"), attempt)
+                time.sleep(1.0 * attempt)
+                continue
+
+            try:
+                apply_callback(new_code)  # внешний код решает: применить или только diff
+                return new_code
+            except Exception as e:
+                on_error_callback(e, attempt)
+                emit_agent_error("bugfixer_apply_error", file=file_path, error=str(e), attempt=attempt)
+                # Небольшая экспоненциальная пауза между попытками
+                time.sleep(1.0 * attempt)
+
+        return None
\ No newline at end of file
```

</details>

<details><summary>app/modules/improver/improvement_planner.py</summary>

```diff
diff --git a/app/modules/improver/improvement_planner.py b/app/modules/improver/improvement_planner.py
index ac1e649..d597d9c 100644
--- a/app/modules/improver/improvement_planner.py
+++ b/app/modules/improver/improvement_planner.py
@@ -0,0 +1,3 @@
+# app/modules/improver/improvement_planner.py
+from __future__ import annotations
+
@@ -2 +5,3 @@ import json
-from typing import Optional
+import re
+from typing import Optional, Dict, Any, List, Union
+
@@ -6,2 +11,4 @@ class ImprovementPlanner:
-    Строит промт для GPT, чтобы получить план улучшений по саммери кода.
-    Также извлекает JSON-ответ с ключами 'plan' и 'comment'.
+    Строит промпт для GPT, чтобы получить план улучшений по саммери кода.
+    Возвращает строковый промпт (совместимо с CodeAnalyzer.chat).
+    Умеет надёжно извлекать {"plan","comment"} из «болтливых» ответов.
+    Поддерживает оба формата плана: строка или список шагов.
@@ -10 +17,42 @@ class ImprovementPlanner:
-    def build_prompt(self, file_path: str, summary: str) -> list[dict]:
+    SYSTEM_MSG = (
+        "Ты — эксперт по улучшению Python-кода. "
+        "Тебе дают краткое описание файла проекта. "
+        "Нужно предложить улучшения логики, устойчивости, читаемости и архитектуры. "
+        "Отвечай строго JSON без пояснений вне JSON. "
+        "Допустимые форматы:\n"
+        "1) {\"plan\": \"многострочный текст\", \"comment\": \"краткая суть\"}\n"
+        "2) {\"plan\": [{\"step\": 1, \"action\": \"...\", \"details\": \"...\"}, ...], \"comment\": \"...\"}\n"
+        "Ключи обязательны: plan, comment."
+    )
+
+    def build_prompt(self, file_path: str, summary: str) -> str:
+        """
+        Возвращает ЕДИНУЮ строку-подсказку для CodeAnalyzer.chat(prompt, system_msg=...).
+        Не используем списки сообщений — это устраняет ошибки новых SDK.
+        """
+        return (
+            f"Путь к файлу: {file_path}\n\n"
+            f"Описание файла:\n{summary}\n\n"
+            "Сформулируй предложения по улучшению. "
+            "Ответ строго в формате JSON (без кода и Markdown-разметки, без пояснений вне JSON). "
+            "Разрешены два варианта:\n"
+            "{\n"
+            '  "plan": "пошаговый план улучшений (многострочный текст)",\n'
+            '  "comment": "краткая суть предлагаемых изменений"\n'
+            "}\n"
+            "ИЛИ\n"
+            "{\n"
+            '  "plan": [\n'
+            '    {"step": 1, "action": "что сделать", "details": "зачем/как"},\n'
+            '    {"step": 2, "action": "...", "details": "..."}\n'
+            "  ],\n"
+            '  "comment": "краткая суть предлагаемых изменений"\n'
+            "}\n"
+        )
+
+    # ── Дополнительно: если где-то в проекте хочется именно messages (например, для логов/панели) ──
+    def build_messages(self, file_path: str, summary: str) -> list[dict]:
+        """
+        Опционально собирает messages (для отображения в UI). Для реального вызова модели
+        используйте build_prompt + CodeAnalyzer.chat(prompt, system_msg=SYSTEM_MSG).
+        """
@@ -12,18 +60,2 @@ class ImprovementPlanner:
-            {
-                "role": "system",
-                "content": (
-                    "Ты — эксперт по улучшению Python-кода. "
-                    "На вход ты получаешь краткое описание файла проекта. "
-                    "Ответь, как можно улучшить логику, устойчивость, читаемость или архитектуру файла."
-                )
-            },
-            {
-                "role": "user",
-                "content": (
-                    f"Путь к файлу: {file_path}\n\n"
-                    f"Описание файла:\n{summary}\n\n"
-                    "Сформулируй предложения по улучшению. "
-                    "Ответ строго в формате JSON:\n"
-                    "{\"plan\": \"описание шагов\", \"comment\": \"суть изменений\"}"
-                )
-            }
+            {"role": "system", "content": self.SYSTEM_MSG},
+            {"role": "user", "content": self.build_prompt(file_path, summary)},
@@ -32 +64 @@ class ImprovementPlanner:
-    def extract_plan(self, gpt_response: str) -> Optional[dict]:
+    def extract_plan(self, gpt_response: str) -> Optional[Dict[str, Any]]:
@@ -35 +67,2 @@ class ImprovementPlanner:
-        Возвращает словарь или None при ошибке.
+        Очень терпеливая обработка: срезает кодовые блоки, ищет подстроку {…}, чинит одинарные кавычки.
+        Возвращает словарь {"plan": <str>, "comment": <str>} или None при ошибке.
@@ -36,0 +70,44 @@ class ImprovementPlanner:
+        if not gpt_response:
+            return None
+
+        text = gpt_response.strip()
+
+        # 1) убрать возможные ```json ... ``` обёртки
+        fence = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
+        m = fence.match(text)
+        if m:
+            text = m.group(1).strip()
+
+        # 2) если это уже валидный JSON
+        data = self._try_json(text)
+        data = self._massage_keys(data)  # подхват нестандартных ключей
+        if self._valid_plan(data):
+            return self._normalize_plan(data)
+
+        # 3) попробовать вытащить самую большую { … } подстроку
+        brace_extract = self._extract_braced_json(text)
+        data = self._try_json(brace_extract)
+        data = self._massage_keys(data)
+        if self._valid_plan(data):
+            return self._normalize_plan(data)
+
+        # 4) грубая замена одинарных кавычек → двойные (внутри извлечённого блока)
+        if brace_extract:
+            fixed = self._single_to_double_quotes(brace_extract)
+            data = self._try_json(fixed)
+            data = self._massage_keys(data)
+            if self._valid_plan(data):
+                return self._normalize_plan(data)
+
+        # 5) как крайняя мера — попытка вытащить план по ключевым словам
+        heuristic = self._heuristic_extract(text)
+        if heuristic:
+            return heuristic
+
+        return None
+
+    # ── helpers ─────────────────────────────────────────────────────────────────
+
+    def _try_json(self, s: Optional[str]) -> Optional[Dict[str, Any]]:
+        if not s:
+            return None
@@ -38,3 +115,2 @@ class ImprovementPlanner:
-            data = json.loads(gpt_response)
-            if isinstance(data, dict) and "plan" in data and "comment" in data:
-                return data
+            obj = json.loads(s)
+            return obj if isinstance(obj, dict) else None
@@ -42 +118,109 @@ class ImprovementPlanner:
-            pass
+            return None
+
+    def _valid_plan(self, data: Optional[Dict[str, Any]]) -> bool:
+        """
+        Валиден, если есть ключи plan и comment.
+        plan может быть строкой ИЛИ непустым списком.
+        """
+        if not isinstance(data, dict):
+            return False
+        keys = {k.lower(): k for k in data.keys()}
+        if "plan" not in keys or "comment" not in keys:
+            return False
+        plan_val = data[keys["plan"]]
+        if isinstance(plan_val, str):
+            return plan_val.strip() != ""
+        if isinstance(plan_val, list):
+            return len(plan_val) > 0
+        return False
+
+    def _massage_keys(self, data: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
+        """
+        Мягкая адаптация: если модель прислала, например, "steps" без "plan", переложим в "plan".
+        """
+        if not isinstance(data, dict):
+            return data
+        if "plan" not in data and "steps" in data:
+            data = dict(data)
+            data["plan"] = data.pop("steps")
+        return data
+
+    def _normalize_plan(self, data: Dict[str, Any]) -> Dict[str, Any]:
+        """
+        Нормализуем ключи к "plan" и "comment" и приводим plan к строке.
+        Поддерживает:
+          - plan: "текст плана"
+          - plan: [{step, action, details}, ...] | ["шаг 1", "..."]
+        """
+        # 1) нормализуем ключи
+        key_map = {}
+        for k in data.keys():
+            lk = k.lower().strip()
+            if lk in ("plan", "план", "steps"):
+                key_map["plan"] = k
+            elif lk in ("comment", "комментарий", "summary", "resume", "суть"):
+                key_map["comment"] = k
+
+        plan_raw: Union[str, List[Any], None] = data.get(key_map.get("plan", ""), "")
+        comment_raw: Any = data.get(key_map.get("comment", ""), "")
+
+        # 2) приводим plan к строке
+        plan_text: str = ""
+        if isinstance(plan_raw, str):
+            plan_text = plan_raw.strip()
+        elif isinstance(plan_raw, list):
+            lines: List[str] = []
+            for i, item in enumerate(plan_raw, start=1):
+                if isinstance(item, dict):
+                    step_num = item.get("step", i)
+                    action = str(item.get("action", "")).strip()
+                    details = str(item.get("details", "")).strip()
+                    if action and details:
+                        lines.append(f"{step_num}. {action} — {details}")
+                    elif action:
+                        lines.append(f"{step_num}. {action}")
+                    elif details:
+                        lines.append(f"{step_num}. {details}")
+                    else:
+                        lines.append(f"{step_num}. (empty step)")
+                else:
+                    lines.append(f"{i}. {str(item).strip()}")
+            plan_text = "\n".join(lines).strip()
+        else:
+            plan_text = ""
+
+        return {
+            "plan": plan_text,
+            "comment": str(comment_raw).strip() if comment_raw is not None else "",
+        }
+
+    def _extract_braced_json(self, s: str) -> Optional[str]:
+        """
+        Возвращает наибольший фрагмент, ограниченный фигурными скобками { … }.
+        """
+        start = s.find("{")
+        last = s.rfind("}")
+        if start == -1 or last == -1 or last <= start:
+            return None
+        return s[start:last + 1]
+
+    def _single_to_double_quotes(self, s: str) -> str:
+        """
+        Грубая, но иногда практичная замена одинарных кавычек на двойные в JSON-фрагменте.
+        """
+        return re.sub(r"(?<!\\)'", '"', s)
+
+    def _heuristic_extract(self, s: str) -> Optional[Dict[str, str]]:
+        """
+        Последняя попытка: вытащить ключевые поля из обычного текста.
+        """
+        plan = ""
+        comment = ""
+        plan_match = re.search(r"(?:^|\n)\s*(?:plan|план)\s*:\s*(.+?)(?:\n\S|$)", s, re.IGNORECASE | re.DOTALL)
+        if plan_match:
+            plan = plan_match.group(1).strip()
+        comment_match = re.search(r"(?:^|\n)\s*(?:comment|комментарий|суть)\s*:\s*(.+?)(?:\n\S|$)", s, re.IGNORECASE | re.DOTALL)
+        if comment_match:
+            comment = comment_match.group(1).strip()
+        if plan or comment:
+            return {"plan": plan, "comment": comment}
@@ -46 +230 @@ class ImprovementPlanner:
-# 👇 Обёртка-функция для использования с SelfImprover
+# 👇 Обёртка-функция для использования с SelfImprover (если где-то используется напрямую)
@@ -47,0 +232,4 @@ def get_improvement_plan(chatgpt, file_path: str, summary: str) -> Optional[dict
+    """
+    Унифицированный вызов: строим строковый промпт и обращаемся к CodeAnalyzer.chat
+    с системным сообщением от планировщика.
+    """
@@ -49,2 +237,2 @@ def get_improvement_plan(chatgpt, file_path: str, summary: str) -> Optional[dict
-    messages = planner.build_prompt(file_path, summary)
-    response = chatgpt.ask(messages)
+    prompt = planner.build_prompt(file_path, summary)
+    response = chatgpt.chat(prompt, system_msg=planner.SYSTEM_MSG)
```

</details>

<details><summary>app/modules/improver/patch_requester.py</summary>

```diff
diff --git a/app/modules/improver/patch_requester.py b/app/modules/improver/patch_requester.py
index 6ff1fd1..998aa59 100644
--- a/app/modules/improver/patch_requester.py
+++ b/app/modules/improver/patch_requester.py
@@ -1 +1,6 @@
-from typing import Optional
+# app/modules/improver/patch_requester.py
+from __future__ import annotations
+
+import re
+from typing import Optional, Dict
+
@@ -5,2 +10,3 @@ class PatchRequester:
-    Генерирует промт для GPT на основании старого кода и плана улучшений.
-    Возвращает новый код в виде единого файла.
+    Генерирует строковый промпт для GPT на основании старого кода и плана улучшений.
+    Ожидается, что модель вернёт ПОЛНЫЙ обновлённый текст файла.
+    Также есть утилита extract_code() для извлечения чистого кода из «болтливых» ответов.
@@ -8,0 +15,7 @@ class PatchRequester:
+    SYSTEM_MSG = (
+        "Ты — помощник-программист. Обновляй код строго по плану улучшений, "
+        "сохраняй работоспособность и смысл логики. Не ломай архитектуру, "
+        "если это явно не требуется. Возвращай ПОЛНЫЙ ТЕКСТ ФАЙЛА. "
+        "Без пояснений вокруг, без Markdown — только код."
+    )
+
@@ -14,4 +27,7 @@ class PatchRequester:
-        plan_data: dict
-    ) -> list[dict]:
-        plan = plan_data.get("plan", "")
-        comment = plan_data.get("comment", "")
+        plan_data: Dict
+    ) -> str:
+        """
+        Возвращает ЕДИНУЮ строку для CodeAnalyzer.chat(prompt, system_msg=...).
+        """
+        plan = plan_data.get("plan", "").strip()
+        comment = plan_data.get("comment", "").strip()
@@ -18,0 +35,14 @@ class PatchRequester:
+        return (
+            f"Путь к файлу: {file_path}\n\n"
+            f"Краткое описание (summary):\n{summary}\n\n"
+            f"Комментарий:\n{comment}\n\n"
+            f"ПЛАН ИЗМЕНЕНИЙ:\n{plan}\n\n"
+            "Исходный код файла ниже. Обнови его, реализовав план, не ломая остальную систему. "
+            "Верни ПОЛНЫЙ обновлённый файл, без Markdown и без дополнительных комментариев.\n\n"
+            "----- НАЧАЛО ИСХОДНИКА -----\n"
+            f"{file_content}\n"
+            "----- КОНЕЦ ИСХОДНИКА -----\n"
+        )
+
+    # Опционально (для UI/логов): если нужно отрисовывать messages
+    def build_messages(self, file_path: str, file_content: str, summary: str, plan_data: Dict) -> list[dict]:
@@ -20,23 +50,2 @@ class PatchRequester:
-            {
-                "role": "system",
-                "content": (
-                    "Ты — помощник-программист. "
-                    "Твоя задача — обновить код на основе предложенного плана улучшений, "
-                    "сохранив работоспособность и смысл логики. "
-                    "Не удаляй важные участки без необходимости. "
-                    "Не изменяй архитектуру, если это не требуется по плану. "
-                    "Ответ должен быть полным обновлённым кодом файла."
-                )
-            },
-            {
-                "role": "user",
-                "content": (
-                    f"Путь к файлу: {file_path}\n\n"
-                    f"Краткое описание файла (summary):\n{summary}\n\n"
-                    f"Комментарий от GPT:\n{comment}\n\n"
-                    f"План улучшений:\n{plan}\n\n"
-                    f"Исходный код файла:\n{file_content}\n\n"
-                    "Пожалуйста, обнови этот код, реализовав указанный план. "
-                    "Ответ должен содержать только обновлённый код файла."
-                )
-            }
+            {"role": "system", "content": self.SYSTEM_MSG},
+            {"role": "user", "content": self.build_prompt(file_path, file_content, summary, plan_data)},
@@ -44,0 +54,27 @@ class PatchRequester:
+    @staticmethod
+    def extract_code(raw: Optional[str]) -> str:
+        """
+        Извлекает «чистый» код из ответа модели:
+        - срезает ```блоки``` (```python ... ```),
+        - удаляет BOM/невидимые символы,
+        - убирает префиксы вроде 'Обновлённый код:'.
+        """
+        if not raw:
+            return ""
+
+        text = raw.strip()
+
+        # 1) убрать ограждения ``` ```
+        fence = re.compile(r"^```(?:\w+)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
+        m = fence.match(text)
+        if m:
+            text = m.group(1).strip()
+
+        # 2) убрать частые префиксы/лейблы
+        text = re.sub(r"^(?:Обновл[её]нный код|Updated code|Code)\s*:\s*", "", text, flags=re.IGNORECASE)
+
+        # 3) убрать BOM и неразрывные пробелы
+        text = text.replace("\ufeff", "").replace("\u00A0", " ")
+
+        return text
+
@@ -45,0 +82 @@ class PatchRequester:
+# 👇 Обёртка — унифицированный вызов из SelfImprover (при необходимости)
@@ -51,2 +88,2 @@ def request_code_patch(
-    plan_data: dict
-) -> Optional[dict]:
+    plan_data: Dict
+) -> Optional[Dict[str, str]]:
@@ -54 +91,2 @@ def request_code_patch(
-    Запрашивает у GPT обновлённый код файла по плану.
+    Запрашивает у GPT обновлённый код по плану. Возвращает {"code": "<новый_файл>"} или None.
+    Совместимо с CodeAnalyzer.chat(prompt, system_msg=...).
@@ -57,3 +95,5 @@ def request_code_patch(
-    messages = requester.build_prompt(file_path, file_content, summary, plan_data)
-    response = chatgpt.ask(messages)
-    return {"code": response} if response else None
\ No newline at end of file
+    prompt = requester.build_prompt(file_path, file_content, summary, plan_data)
+    # Рекомендуется передавать строгий system_msg, чтобы модель не болтала
+    raw = chatgpt.chat(prompt, system_msg=requester.SYSTEM_MSG)
+    code = requester.extract_code(raw)
+    return {"code": code} if code else None
\ No newline at end of file
```

</details>

<details><summary>app/modules/improver/patcher.py</summary>

```diff
diff --git a/app/modules/improver/patcher.py b/app/modules/improver/patcher.py
index 6406968..a31f1f5 100644
--- a/app/modules/improver/patcher.py
+++ b/app/modules/improver/patcher.py
@@ -0,0 +1,3 @@
+# app/modules/improver/patcher.py
+from __future__ import annotations
+
@@ -3,0 +7,2 @@ import difflib
+import json
+import time
@@ -4,0 +10,10 @@ from datetime import datetime
+from pathlib import Path
+from typing import Optional, Tuple, Any, Dict
+
+from app.logger import log_info, log_error, log_warning
+
+try:
+    # Опциональная интеграция с централизованным менеджером файлов (если есть)
+    from app.core.file_manager import FileManager as CoreFileManager  # type: ignore
+except Exception:
+    CoreFileManager = None  # не требуем наличия
@@ -6 +20,0 @@ from datetime import datetime
-from app.logger import log_info, log_error
@@ -12 +26 @@ class CodePatcher:
-    - показывает diff,
+    - показывает/сохраняет diff,
@@ -14 +28,7 @@ class CodePatcher:
-    - сохраняет .diff отдельно.
+    - сохраняет .diff отдельно,
+    - сохраняет metadata о применённом патче (JSON).
+
+    Обратная совместимость:
+      - confirm_and_apply_patch(file_path, old_code, new_code) -> (backup_path, diff_path)
+      - apply_patch_no_prompt(file_path, old_code, new_code, *, save_backup, save_diff, save_only, interactive_confirm)
+      - _save_diff(file_path, diff_text) И _save_diff(file_path, old_code, new_code) — оба варианта поддержаны
@@ -17,5 +37,23 @@ class CodePatcher:
-    def __init__(self, backup_dir="app/backups", diff_dir="app/patches"):
-        self.backup_dir = backup_dir
-        self.diff_dir = diff_dir
-        os.makedirs(self.backup_dir, exist_ok=True)
-        os.makedirs(self.diff_dir, exist_ok=True)
+    def __init__(
+        self,
+        backup_dir: str = "app/backups",
+        diff_dir: str = "app/patches",
+        *,
+        file_manager: Optional["CoreFileManager"] = None,  # опционально
+        diffs_dirname_nested: bool = True,                 # складывать дифы по относительным подпапкам
+        context_lines: int = 3
+    ):
+        self.backup_dir = Path(backup_dir)
+        self.diff_dir = Path(diff_dir)
+        self.fm = file_manager if CoreFileManager and isinstance(file_manager, CoreFileManager) else None
+        self.diffs_dirname_nested = diffs_dirname_nested
+        self.context_lines = int(context_lines)
+
+        # гарантируем каталоги
+        self.backup_dir.mkdir(parents=True, exist_ok=True)
+        self.diff_dir.mkdir(parents=True, exist_ok=True)
+
+        log_info(
+            f"[CodePatcher] init backup_dir={self.backup_dir} diff_dir={self.diff_dir} "
+            f"core_fm={'on' if self.fm else 'off'}"
+        )
@@ -23 +61,3 @@ class CodePatcher:
-    def confirm_and_apply_patch(self, file_path, old_code, new_code):
+    # ---------- Публичные методы ----------
+
+    def confirm_and_apply_patch(self, file_path: str, old_code: str, new_code: str) -> Tuple[Optional[str], Optional[str]]:
@@ -25 +65,2 @@ class CodePatcher:
-        Показывает diff и предлагает применить изменения.
+        Интерактивное применение патча с вопросом в консоли.
+        Возвращает (backup_path, diff_path).
@@ -27,3 +68,4 @@ class CodePatcher:
-        diff = self._generate_diff(file_path, old_code, new_code)
-        self._save_diff(file_path, diff)
-        print(diff)
+        file_path = str(self._norm(file_path))
+        diff_text = self._generate_diff(file_path, old_code, new_code)
+        diff_path = self._save_diff(file_path, diff_text)  # совместимо с новой сигнатурой
+        print(diff_text)
@@ -34 +76 @@ class CodePatcher:
-            return
+            return None, diff_path
@@ -36 +78 @@ class CodePatcher:
-        self._backup(file_path)
+        backup_path = self._backup(file_path)
@@ -37,0 +80,38 @@ class CodePatcher:
+        self._save_metadata(file_path, old_code, new_code, diff_path, interactive=True)
+        return backup_path, diff_path
+
+    def apply_patch_no_prompt(
+        self,
+        file_path: str,
+        old_code: str,
+        new_code: str,
+        *,
+        save_backup: bool = True,
+        save_diff: bool = True,
+        # ↓↓↓ параметры для обратной совместимости с новыми вызовами
+        save_only: Optional[bool] = None,
+        interactive_confirm: Optional[bool] = None,
+    ) -> Tuple[Optional[str], Optional[str]]:
+        """
+        Неинтерактивное применение патча — используется в авто-режимах.
+        Возвращает (backup_path, diff_path).
+
+        Аргументы:
+          - save_backup: делать ли .bak перед записью
+          - save_diff: сохранять ли diff-файл
+          - save_only: (для совместимости) если True — НЕ перезаписывать файл, только сохранить diff
+          - interactive_confirm: игнорируется (неинтерактивный метод), оставлен для совместимости
+        """
+        file_path = str(self._norm(file_path))
+
+        # save_only имеет приоритет
+        if isinstance(save_only, bool):
+            if save_only:
+                save_backup_effective = False
+                apply_code = False
+            else:
+                save_backup_effective = save_backup
+                apply_code = True
+        else:
+            save_backup_effective = save_backup
+            apply_code = True
@@ -39 +119,24 @@ class CodePatcher:
-    def _backup(self, file_path):
+        diff_path = None
+        if save_diff:
+            # поддерживаем вызов _save_diff(file_path, old, new)
+            diff_path = self._save_diff(file_path, old_code, new_code)
+
+        backup_path = None
+        if apply_code:
+            if save_backup_effective:
+                backup_path = self._backup(file_path)
+            self._write_code(file_path, new_code)
+            self._save_metadata(file_path, old_code, new_code, diff_path, interactive=False)
+            log_info(f"[CodePatcher] ✅ Патч применён: {file_path}")
+        else:
+            log_info(f"[CodePatcher] 📝 Diff сохранён без применения патча: {file_path}")
+
+        return backup_path, diff_path
+
+    # ---------- Внутренние утилиты ----------
+
+    def _backup(self, file_path: str) -> Optional[str]:
+        """
+        Создаёт копию целевого файла в backup_dir. Если файла нет — просто логируем.
+        """
+        src = Path(file_path)
@@ -41,2 +144,6 @@ class CodePatcher:
-        filename = os.path.basename(file_path)
-        dst = os.path.join(self.backup_dir, f"{filename}.{ts}.bak")
+        dst = self.backup_dir / f"{src.name}.{ts}.bak"
+
+        if not src.exists():
+            log_warning(f"[CodePatcher] Бэкап пропущен: файл не найден для {src}")
+            return None
+
@@ -44 +151,2 @@ class CodePatcher:
-            shutil.copy2(file_path, dst)
+            dst.parent.mkdir(parents=True, exist_ok=True)
+            shutil.copy2(str(src), str(dst))
@@ -45,0 +154 @@ class CodePatcher:
+            return str(dst)
@@ -47,0 +157 @@ class CodePatcher:
+            return None
@@ -49 +159,5 @@ class CodePatcher:
-    def _write_code(self, file_path, new_code):
+    def _write_code(self, file_path: str, new_code: str) -> None:
+        """
+        Пишем новый код. Если присутствует CoreFileManager — используем его атомарную запись.
+        """
+        p = Path(file_path)
@@ -51,3 +165,8 @@ class CodePatcher:
-            with open(file_path, "w", encoding="utf-8") as f:
-                f.write(new_code)
-            log_info(f"[CodePatcher] ✅ Код обновлён: {file_path}")
+            p.parent.mkdir(parents=True, exist_ok=True)
+            if self.fm:
+                # атомарная запись через CoreFileManager
+                self.fm.write_text(p, new_code)  # type: ignore[arg-type]
+            else:
+                with open(p, "w", encoding="utf-8", newline="") as f:
+                    f.write(new_code)
+            log_info(f"[CodePatcher] ✅ Код обновлён: {p}")
@@ -55 +174,2 @@ class CodePatcher:
-            log_error(f"[CodePatcher] ❌ Ошибка при записи файла: {e}")
+            log_error(f"[CodePatcher] ❌ Ошибка при записи файла '{p}': {e}")
+            raise
@@ -57,3 +177,3 @@ class CodePatcher:
-    def _generate_diff(self, path, old_code, new_code):
-        old_lines = old_code.splitlines(keepends=True)
-        new_lines = new_code.splitlines(keepends=True)
+    def _generate_diff(self, path: str, old_code: str, new_code: str) -> str:
+        old_lines = (old_code or "").splitlines(keepends=True)
+        new_lines = (new_code or "").splitlines(keepends=True)
@@ -61 +181,2 @@ class CodePatcher:
-            old_lines, new_lines,
+            old_lines,
+            new_lines,
@@ -63,0 +185 @@ class CodePatcher:
+            n=self.context_lines,
@@ -68,4 +190,10 @@ class CodePatcher:
-    def _save_diff(self, file_path, diff_text):
-        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
-        filename = os.path.basename(file_path)
-        diff_file = os.path.join(self.diff_dir, f"{filename}.{ts}.diff.txt")
+    def _save_diff(self, file_path: str, *args: Any) -> Optional[str]:
+        """
+        Бэкенд-совместимая функция сохранения diff.
+
+        Варианты вызова:
+          1) _save_diff(file_path, diff_text)
+          2) _save_diff(file_path, old_code, new_code)
+
+        Возвращает путь к сохранённому diff-файлу или None при ошибке.
+        """
@@ -73,3 +201,22 @@ class CodePatcher:
-            with open(diff_file, "w", encoding="utf-8") as f:
-                f.write(diff_text)
-            log_info(f"[CodePatcher] 💾 Diff сохранён: {diff_file}")
+            if len(args) == 1:
+                # Старый вызов: вторым параметром уже готовый diff_text
+                diff_text = str(args[0])
+            elif len(args) == 2:
+                # Новый вызов: переданы old_code и new_code
+                old_code, new_code = args
+                diff_text = self._generate_diff(file_path, str(old_code), str(new_code))
+            else:
+                raise TypeError(f"_save_diff() ожидает 2 или 3 аргумента, получено: {1 + len(args)}")
+
+            out_file = self._make_diff_output_path(file_path)
+            out_file.parent.mkdir(parents=True, exist_ok=True)
+
+            if self.fm:
+                self.fm.write_text(out_file, diff_text)  # type: ignore[arg-type]
+            else:
+                with open(out_file, "w", encoding="utf-8", newline="") as f:
+                    f.write(diff_text)
+
+            log_info(f"[CodePatcher] 💾 Diff сохранён: {out_file}")
+            return str(out_file)
+
@@ -77 +224,91 @@ class CodePatcher:
-            log_error(f"[CodePatcher] ❌ Ошибка при сохранении diff: {e}")
\ No newline at end of file
+            log_error(f"[CodePatcher] ❌ Ошибка при сохранении diff: {e}")
+            return None
+
+    # ---------- Дополнительно: метаданные и пути ----------
+
+    def _save_metadata(
+        self,
+        file_path: str,
+        old_code: str,
+        new_code: str,
+        diff_path: Optional[str],
+        interactive: bool
+    ) -> None:
+        """
+        Сохраняем метаданные о применённом патче рядом с .diff:
+        - change_id, timestamps
+        - пути, размеры, хэши (если CoreFileManager доступен)
+        - режим применения (interactive/auto)
+        """
+        try:
+            change_id = f"{int(time.time())}"
+            meta: Dict[str, Any] = {
+                "change_id": change_id,
+                "file": str(Path(file_path).resolve()),
+                "diff_path": diff_path,
+                "mode": "interactive" if interactive else "auto",
+                "applied_at": datetime.now().isoformat(timespec="seconds"),
+                "old_len": len(old_code or ""),
+                "new_len": len(new_code or ""),
+            }
+
+            # Хэши, если есть CoreFileManager
+            if self.fm:
+                p = Path(file_path).resolve()
+                try:
+                    meta["new_hash_sha256"] = self.fm.compute_hash(p, algo="sha256")  # type: ignore[arg-type]
+                except Exception:
+                    pass
+
+            meta_path = self._make_diff_output_path(file_path, suffix=".meta.json")
+            meta_path.parent.mkdir(parents=True, exist_ok=True)
+
+            payload = json.dumps(meta, ensure_ascii=False, indent=2)
+            if self.fm:
+                self.fm.write_text(meta_path, payload)  # type: ignore[arg-type]
+            else:
+                with open(meta_path, "w", encoding="utf-8", newline="") as f:
+                    f.write(payload)
+
+            log_info(f"[CodePatcher] 🧾 Metadata сохранена: {meta_path}")
+        except Exception as e:
+            log_warning(f"[CodePatcher] Не удалось сохранить metadata: {e}")
+
+    def _make_diff_output_path(self, file_path: str, *, suffix: str = ".diff.txt") -> Path:
+        """
+        Генерация пути для diff/metadata:
+        - Если diffs_dirname_nested=True и файл лежит внутри известной базы (sandbox или fm.base_dir),
+          сохраняем в подпапках, повторяя структуру.
+        - Иначе — в корне diff_dir.
+        """
+        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
+        src = Path(file_path).resolve()
+
+        # База для относительного пути
+        base_candidates = []
+        if self.fm:
+            base_candidates.append(self.fm.base_dir)  # type: ignore[attr-defined]
+        # Евристика: если файл расположен внутри app/, положим дифы зеркально
+        base_candidates.append(Path.cwd())
+        chosen_rel = None
+
+        if self.diffs_dirname_nested:
+            for base in base_candidates:
+                try:
+                    rel = src.relative_to(Path(base).resolve())
+                    chosen_rel = rel
+                    break
+                except Exception:
+                    continue
+
+        if chosen_rel:
+            # app/agent/x.py -> app/patches/app/agent/x.py.<ts>.diff.txt
+            out_file = self.diff_dir / chosen_rel
+            out_file = out_file.with_name(f"{out_file.name}.{ts}{suffix}")
+        else:
+            out_file = self.diff_dir / f"{src.name}.{ts}{suffix}"
+
+        return out_file
+
+    def _norm(self, p: str | os.PathLike) -> Path:
+        return Path(p).expanduser().resolve()
\ No newline at end of file
```

</details>

<details><summary>app/modules/improver/project_scanner.py</summary>

```diff
diff --git a/app/modules/improver/project_scanner.py b/app/modules/improver/project_scanner.py
index 8c339f2..a7599ef 100644
--- a/app/modules/improver/project_scanner.py
+++ b/app/modules/improver/project_scanner.py
@@ -10 +10 @@ from datetime import datetime
-from typing import Dict, Any, List
+from typing import Dict, Any, List, Optional, Tuple
@@ -13 +12,0 @@ from app.logger import log_info, log_warning, log_error
-from app.modules.improver.file_summarizer import FileSummarizer
@@ -15 +14,9 @@ from app.modules.improver.file_summarizer import FileSummarizer
-SCAN_CACHE_PATH = "app/data/scan_cache.json"
+# Лёгкая зависимость опциональна в ранних ветках
+try:
+    from app.modules.improver.file_summarizer import FileSummarizer  # type: ignore
+except Exception:
+    FileSummarizer = None  # type: ignore
+
+SCAN_CACHE_PATH = os.path.abspath("app/data/scan_cache.json")
+
+# Разрешённые расширения (оставил .py по-умолчанию; при желании дополни)
@@ -17,0 +25 @@ ALLOWED_EXTENSIONS = {".py"}
+# Папки/паттерны, которые исключаем
@@ -19,2 +27,4 @@ IGNORE_FOLDERS = {
-    "sandbox", "venv", ".venv", "env", "__pycache__", ".git",
-    "site-packages", "frontend_old", "tests", "testdata"
+    "sandbox", "venv", ".venv", "env", "__pycache__", ".git", "site-packages",
+    "frontend_old", "tests", "testdata",
+    # исключаем внутренние артефакты самоулучшения
+    "backups", "patches", ".aideon_backups"
@@ -23,0 +34,3 @@ IGNORE_PATTERNS = ["копия", "copy", "backup", "tmp", "bak", "~"]
+# Лимит размера файла (в КБ), чтобы не валить LLM и не тормозить скан
+MAX_FILE_KB = 1024  # 1 МБ
+
@@ -25,2 +38,2 @@ IGNORE_PATTERNS = ["копия", "copy", "backup", "tmp", "bak", "~"]
-def is_hidden(filename: str) -> bool:
-    return filename.startswith(".") or filename.startswith("_")
+def _is_hidden(name: str) -> bool:
+    return name.startswith(".") or name.startswith("_")
@@ -29,2 +42,2 @@ def is_hidden(filename: str) -> bool:
-def is_copy_or_temp(filename: str) -> bool:
-    low = filename.lower()
+def _is_copy_or_temp(name: str) -> bool:
+    low = name.lower()
@@ -33,0 +47,5 @@ def is_copy_or_temp(filename: str) -> bool:
+def _split_ext_lower(path: str) -> Tuple[str, str]:
+    base, ext = os.path.splitext(path)
+    return base, ext.lower()
+
+
@@ -36,9 +54,19 @@ class ProjectScanner:
-    🔍 Сканирует проект, исключая sandbox/venv/копии.
-    Формирует дерево файлов и кэширует результаты.
-
-    Теперь для каждого файла:
-      - summary: dict {
-          lines, classes, functions, todos, tags, status, raw_summary
-        }
-      - structure: dict {lines, classes_count, functions_count, class_names, function_names}
-        (для обратной совместимости с прежними потребителями)
+    🔍 Сканирует проект (по-умолчанию 'app') c кэшированием метасаммери.
+    Возвращаемая структура:
+      {
+        "<rel_dir>": [
+          {
+            "name": "main_window.py",
+            "rel_dir": "ui",                              # без префикса app/
+            "rel_path": "app/ui/main_window.py",         # нормализованный относительный путь
+            "abs_path": "/abs/.../app/ui/main_window.py",
+            "size": 12345,
+            "ext": ".py",
+            "summary": { ... богатая сводка ... },
+            "structure": { ... legacy компакт ... },
+            "skipped": False,
+            "reason": None
+          },
+          ...
+        ]
+      }
@@ -47,0 +76 @@ class ProjectScanner:
+        # Нормализуем корень
@@ -48,0 +78,6 @@ class ProjectScanner:
+        if os.path.basename(self.root_path) != "app":
+            # защищаемся от двойного app/app
+            candidate = os.path.join(self.root_path, "app")
+            if os.path.isdir(candidate):
+                self.root_path = os.path.abspath(candidate)
+
@@ -51 +86,3 @@ class ProjectScanner:
-        self.summarizer = FileSummarizer()
+        self.summarizer = FileSummarizer() if FileSummarizer else None
+
+    # -------------------- ПУБЛИЧНОЕ АПИ --------------------
@@ -55,0 +93 @@ class ProjectScanner:
+        total_files = 0
@@ -58 +96 @@ class ProjectScanner:
-            # фильтруем поддиректории на месте
+            # Фильтруем поддиректории inplace
@@ -61,3 +99,3 @@ class ProjectScanner:
-                if not self._should_ignore(os.path.join(dirpath, d))
-                and not is_hidden(d)
-                and not is_copy_or_temp(d)
+                if not self._should_ignore_dir(os.path.join(dirpath, d))
+                and not _is_hidden(d)
+                and not _is_copy_or_temp(d)
@@ -67 +105,3 @@ class ProjectScanner:
-            valid_files: List[Dict[str, Any]] = []
+            if rel_dir == ".":
+                rel_dir = ""  # корень 'app' → пустая строка для красивых путей
+            bucket: List[Dict[str, Any]] = []
@@ -70 +110,12 @@ class ProjectScanner:
-                if not self._is_valid_file(fname, dirpath):
+                abs_path = os.path.join(dirpath, fname)
+                base, ext = _split_ext_lower(fname)
+
+                # Фильтры на файл
+                reason = self._file_skip_reason(fname=fname, dirpath=dirpath, ext=ext)
+                if reason:
+                    # пропуск без лог-спама — это норма
+                    continue
+
+                size = self._safe_size(abs_path)
+                if size is None:
+                    log_warning(f"[ProjectScanner] ⚠️ Не удалось получить размер: {abs_path}")
@@ -71,0 +123,7 @@ class ProjectScanner:
+                if (size / 1024.0) > MAX_FILE_KB:
+                    # слишком большой — игнорируем
+                    continue
+
+                # Ключ для кэша: быстрый (size + mtime) + sha256 при изменении
+                mtime = self._safe_mtime(abs_path)
+                fast_key = f"{size}:{int(mtime or 0)}"
@@ -73,2 +131,2 @@ class ProjectScanner:
-                full_path = os.path.join(dirpath, fname)
-                file_hash = self._hash_file(full_path)
+                cached = self.cache.get(abs_path)
+                cache_key = cached.get("fast_key") if isinstance(cached, dict) else None
@@ -76,3 +134,2 @@ class ProjectScanner:
-                # --- Попытка взять из кэша ---
-                cached = self.cache.get(full_path)
-                if cached and cached.get("hash") == file_hash:
+                # Если быстрый ключ совпал → используем кэш как есть
+                if cached and cache_key == fast_key:
@@ -80,2 +137,2 @@ class ProjectScanner:
-                    structure = cached.get("structure")  # legacy совместимость
-                    # мигрируем старый формат (строка) в dict
+                    structure = cached.get("structure")
+                    # Бэк-компат для старых строковых summary
@@ -83,9 +140,2 @@ class ProjectScanner:
-                        summary = {
-                            "lines": None,
-                            "classes": None,
-                            "functions": None,
-                            "todos": 0,
-                            "tags": None,
-                            "status": "legacy",
-                            "raw_summary": summary,
-                        }
+                        summary = self._wrap_legacy_summary(summary)
+                    self._touch_cache(abs_path, fast_key, summary, structure)
@@ -94,6 +144,5 @@ class ProjectScanner:
-                    # --- Читаем файл и строим summary ---
-                    try:
-                        with open(full_path, "r", encoding="utf-8") as f:
-                            content = f.read()
-                    except Exception as e:
-                        log_warning(f"[ProjectScanner] ⚠️ Ошибка при чтении {fname}: {e}")
+                    # Иначе — считаем sha и заново строим
+                    file_hash = self._sha256(abs_path)
+                    text = self._read_text(abs_path)
+                    if text is None:
+                        log_warning(f"[ProjectScanner] ⚠️ Ошибка чтения файла: {abs_path}")
@@ -102,17 +151,4 @@ class ProjectScanner:
-                    # 1) Человеческое краткое описание
-                    try:
-                        raw_text = self.summarizer.summarize(full_path, content)
-                    except Exception as e:
-                        raw_text = f"(summarizer error: {e})"
-
-                    # 2) Структура (AST → fallback regex), + теги/статус/todo
-                    structure_full = self._structure_full(full_path, content)
-
-                    # 3) summary dict (богатая версия)
-                    summary = {
-                        **structure_full,
-                        "raw_summary": raw_text,
-                    }
-
-                    # 4) legacy structure (counts + имена)
-                    structure = self._structure_legacy(structure_full)
+                    raw_summary = self._call_summarizer(abs_path, text)
+                    full_struct = self._structure_full(abs_path, text)
+                    summary = {**full_struct, "raw_summary": raw_summary}
+                    structure = self._structure_legacy(full_struct)
@@ -119,0 +156 @@ class ProjectScanner:
+                    self._write_cache(abs_path, fast_key, file_hash, summary, structure)
@@ -122,3 +159,8 @@ class ProjectScanner:
-                # --- Обновляем кэш и дерево ---
-                self.updated_cache[full_path] = {
-                    "hash": file_hash,
+                rel_path = self._build_rel_path(rel_dir, fname)   # "app/<rel_dir>/fname"
+                file_entry: Dict[str, Any] = {
+                    "name": fname,
+                    "rel_dir": rel_dir,
+                    "rel_path": rel_path,
+                    "abs_path": abs_path,
+                    "size": size,
+                    "ext": ext,
@@ -126,2 +168,3 @@ class ProjectScanner:
-                    "structure": structure,  # оставляем для совместимости
-                    "timestamp": datetime.now().isoformat(),
+                    "structure": structure,
+                    "skipped": False,
+                    "reason": None,
@@ -128,0 +172,2 @@ class ProjectScanner:
+                bucket.append(file_entry)
+                total_files += 1
@@ -130,7 +175,2 @@ class ProjectScanner:
-                file_entry: Dict[str, Any] = {"name": fname, "summary": summary}
-                if structure is not None:
-                    file_entry["structure"] = structure
-                valid_files.append(file_entry)
-
-            if valid_files:
-                tree[rel_dir] = valid_files
+            if bucket:
+                tree[rel_dir] = bucket
@@ -139 +179 @@ class ProjectScanner:
-        log_info("[ProjectScanner] ✅ Сканирование завершено.")
+        log_info(f"[ProjectScanner] ✅ Сканирование завершено. Файлов к обработке: {total_files}")
@@ -142,29 +182 @@ class ProjectScanner:
-    # ----------------- helpers -----------------
-
-    def _should_ignore(self, path: str) -> bool:
-        norm = os.path.normpath(path)
-        path_parts = set(norm.split(os.sep))
-        return bool(IGNORE_FOLDERS & path_parts)
-
-    def _is_valid_file(self, filename: str, dirpath: str) -> bool:
-        _, ext = os.path.splitext(filename.lower())
-        if ext not in ALLOWED_EXTENSIONS:
-            return False
-        if filename.startswith("_") or filename.startswith("."):
-            return False
-        if is_copy_or_temp(filename):
-            return False
-        if self._should_ignore(dirpath):
-            return False
-        return True
-
-    def _hash_file(self, path: str) -> str:
-        try:
-            hasher = hashlib.sha256()
-            with open(path, "rb") as f:
-                for chunk in iter(lambda: f.read(8192), b""):
-                    hasher.update(chunk)
-            return hasher.hexdigest()
-        except Exception as e:
-            log_error(f"[ProjectScanner] ❌ Не удалось хэшировать файл {path}: {e}")
-            return ""
+    # -------------------- CACHE --------------------
@@ -177 +189,2 @@ class ProjectScanner:
-                return json.load(f)
+                data = json.load(f)
+                return data if isinstance(data, dict) else {}
@@ -191 +204,101 @@ class ProjectScanner:
-    # ----------------- structure extraction -----------------
+    def _touch_cache(self, abs_path: str, fast_key: str, summary: Any, structure: Any) -> None:
+        self.updated_cache[abs_path] = {
+            "fast_key": fast_key,
+            "hash": None,  # может быть не нужен, если fast_key совпал
+            "summary": summary,
+            "structure": structure,
+            "timestamp": datetime.now().isoformat(),
+        }
+
+    def _write_cache(self, abs_path: str, fast_key: str, file_hash: Optional[str],
+                     summary: Any, structure: Any) -> None:
+        self.updated_cache[abs_path] = {
+            "fast_key": fast_key,
+            "hash": file_hash,
+            "summary": summary,
+            "structure": structure,
+            "timestamp": datetime.now().isoformat(),
+        }
+
+    # -------------------- FILE / PATH HELPERS --------------------
+
+    def _should_ignore_dir(self, abs_dir: str) -> bool:
+        # Сравниваем по сегментам пути
+        norm = os.path.normpath(abs_dir)
+        parts = set(norm.split(os.sep))
+        return bool(IGNORE_FOLDERS & parts)
+
+    def _file_skip_reason(self, fname: str, dirpath: str, ext: str) -> Optional[str]:
+        if ext not in ALLOWED_EXTENSIONS:
+            return "ext"
+        if _is_hidden(fname):
+            return "hidden"
+        if _is_copy_or_temp(fname):
+            return "temp"
+        if self._should_ignore_dir(dirpath):
+            return "ignored_dir"
+        return None
+
+    def _safe_size(self, abs_path: str) -> Optional[int]:
+        try:
+            return os.path.getsize(abs_path)
+        except Exception:
+            return None
+
+    def _safe_mtime(self, abs_path: str) -> Optional[float]:
+        try:
+            return os.path.getmtime(abs_path)
+        except Exception:
+            return None
+
+    def _read_text(self, abs_path: str) -> Optional[str]:
+        try:
+            with open(abs_path, "r", encoding="utf-8") as f:
+                return f.read()
+        except Exception:
+            # пробуем без указания encoding
+            try:
+                with open(abs_path, "r") as f:
+                    return f.read()
+            except Exception:
+                return None
+
+    def _sha256(self, abs_path: str) -> Optional[str]:
+        try:
+            h = hashlib.sha256()
+            with open(abs_path, "rb") as f:
+                for chunk in iter(lambda: f.read(8192), b""):
+                    h.update(chunk)
+            return h.hexdigest()
+        except Exception as e:
+            log_error(f"[ProjectScanner] ❌ Не удалось хэшировать файл {abs_path}: {e}")
+            return None
+
+    def _build_rel_path(self, rel_dir: str, fname: str) -> str:
+        # rel_dir приходит уже БЕЗ 'app/'. Здесь гарантируем "app/<rel_dir>/fname"
+        rel_dir = rel_dir.lstrip("/\\")
+        if rel_dir == "":
+            return os.path.join("app", fname).replace("\\", "/")
+        return os.path.join("app", rel_dir, fname).replace("\\", "/")
+
+    # -------------------- SUMMARY / STRUCTURE --------------------
+
+    def _call_summarizer(self, file_path: str, content: str) -> str:
+        if self.summarizer is None:
+            # Мягкая деградация на старых ветках
+            return "(summarizer disabled)"
+        try:
+            return self.summarizer.summarize(file_path, content)
+        except Exception as e:
+            return f"(summarizer error: {e})"
+
+    def _wrap_legacy_summary(self, text: str) -> Dict[str, Any]:
+        return {
+            "lines": None,
+            "classes": None,
+            "functions": None,
+            "todos": 0,
+            "tags": None,
+            "status": "legacy",
+            "raw_summary": text,
+        }
@@ -257 +370 @@ class ProjectScanner:
-        if "/ui/" in low_path or base == "main_window.py":
+        if f"{os.sep}ui{os.sep}" in low_path or base == "main_window.py":
@@ -261 +374 @@ class ProjectScanner:
-        if "/improver/" in low_path:
+        if f"{os.sep}improver{os.sep}" in low_path:
@@ -263 +376 @@ class ProjectScanner:
-        if "/core/" in low_path:
+        if f"{os.sep}core{os.sep}" in low_path:
@@ -265 +378 @@ class ProjectScanner:
-        if "/tests" in low_path or "test" in base:
+        if f"{os.sep}tests" in low_path or "test" in base:
@@ -280 +393 @@ class ProjectScanner:
-        return tags
\ No newline at end of file
+        return sorted(set(tags))
\ No newline at end of file
```

</details>

<details><summary>"app/modules/improver/project_scanner\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"</summary>

_No textual diff (binary or rename)._

</details>

<details><summary>app/modules/self_improver.py</summary>

```diff
diff --git a/app/modules/self_improver.py b/app/modules/self_improver.py
index c756a1d..cd2bb5d 100644
--- a/app/modules/self_improver.py
+++ b/app/modules/self_improver.py
@@ -0,0 +1,3 @@
+# app/modules/self_improver.py
+from __future__ import annotations
+
@@ -2 +5,2 @@ import os
-from datetime import datetime
+import ast
+from typing import Generator, Optional, Dict, Any, Iterable, List, Tuple
@@ -13,0 +18,37 @@ from app.logger import log_info, log_warning, log_error
+from app.modules.improver.ai_bug_fixer import AIBugFixer
+
+
+# ───────────────────────── настройки по умолчанию ─────────────────────────
+
+DEFAULT_ROOT = "app"
+DEFAULT_INCLUDE_EXTS: Tuple[str, ...] = (".py",)
+
+DEFAULT_EXCLUDE_DIRS = {
+    ".git", ".hg", ".svn", ".idea", ".vscode",
+    "__pycache__", "venv", ".venv",
+    "app/logs", "app/patches", "app/backups",
+}
+
+# «бережные» зоны (ядро), куда по умолчанию не пишем
+DEFAULT_SENSITIVE_DIRS = {"app/agent", "app/core"}
+
+HEARTBEAT_EVERY = 2  # как часто печатать прогресс
+
+
+def _nice_rel(path: str, base: str) -> str:
+    try:
+        return os.path.relpath(path, base)
+    except Exception:
+        return path
+
+
+def _to_abs(base_root: str, rel_or_name: str) -> str:
+    """Конвертирует относительный путь в абсолютный, имена оставляет как есть."""
+    if os.path.isabs(rel_or_name):
+        return os.path.normpath(rel_or_name)
+    # если это «короткое имя папки» (например, '__pycache__'), пусть остаётся именем
+    if os.sep not in rel_or_name and "/" not in rel_or_name:
+        return rel_or_name
+    return os.path.normpath(os.path.join(base_root, rel_or_name))
+
+
@@ -16,8 +57,2 @@ class SelfImprover:
-    AI-модуль самоусовершенствования Aideon.
-    Цикл:
-    - сканирует проект с помощью ProjectScanner,
-    - строит метасаммери каждого файла,
-    - отправляет summary для генерации плана улучшений,
-    - запрашивает обновлённый код,
-    - сравнивает, применяет или отлаживает при ошибке.
-    Может интегрироваться с ChatPanel для вывода GPT-запросов и ответов.
+    Глобальный AI-модуль самоусовершенствования Aideon.
+    Цикл по проекту: скан → кандидаты → summary → (опц.) bugfix → план → патч → diff/apply.
@@ -26,2 +61,5 @@ class SelfImprover:
-    def __init__(self, config, chat_panel=None, apply_patches_automatically: bool = False):
-        self.config = config
+    def __init__(self, config: Dict[str, Any] | None, chat_panel=None, apply_patches_automatically: bool = False):
+        self.config = dict(config or {})
+        self.chat_panel = chat_panel
+
+        # Менеджер файлов определяет базу репозитория
@@ -29,3 +67,12 @@ class SelfImprover:
-        self.chatgpt = CodeAnalyzer(config)
-        self.backup_path = "app/backups"
-        self.diff_path = "app/patches"
+        fm_base = getattr(self.file_manager, "base_dir", None)
+
+        # project_root: приоритет — явный конфиг → FileManager.base_dir → CWD
+        self.project_root: str = os.path.abspath(
+            self.config.get("project_root", fm_base if fm_base else os.getcwd())
+        )
+
+        self.chatgpt = CodeAnalyzer(self.config)
+
+        # Пути бэкапов/диффов
+        self.backup_path = self.config.get("backups_dir", "app/backups")
+        self.diff_path = self.config.get("diffs_dir", "app/patches")
@@ -33,0 +81,2 @@ class SelfImprover:
+
+        # Модули пайплайна
@@ -39 +87,0 @@ class SelfImprover:
-        self.chat_panel = chat_panel  # Для вывода GPT-запросов/ответов в интерфейс (может быть None)
@@ -41 +89 @@ class SelfImprover:
-        # Управление процессом
+        # Флаги/управление
@@ -43 +91,3 @@ class SelfImprover:
-        self.apply_patches_automatically = bool(apply_patches_automatically)
+        self.auto_bugfix = bool(self.config.get("auto_bugfix", True))
+        self.max_fix_cycles = int(self.config.get("max_fix_cycles", 2))
+        self.auto_apply_patches = bool(self.config.get("auto_apply_patches", apply_patches_automatically))
@@ -45,7 +95,115 @@ class SelfImprover:
-    def run_self_improvement(self):
-        """
-        Основной генератор логов/шагов самоусовершенствования.
-        Выводит этапы в чат (если задан chat_panel).
-        """
-        log_info("🧠 ▶️ Запущен процесс самоусовершенствования Aideon...")
-        yield "🧠 ▶️ Запущен процесс самоусовершенствования Aideon..."
+        # Фильтры обхода
+        self.include_exts: Tuple[str, ...] = tuple(self.config.get("include_exts", DEFAULT_INCLUDE_EXTS))
+
+        # Нормализуем exclude/sensitive: храним как МИКС из «коротких имён» и «абсолютных префиксов»
+        raw_exclude = set(DEFAULT_EXCLUDE_DIRS) | set(self.config.get("exclude_dirs", []))
+        raw_sensitive = set(DEFAULT_SENSITIVE_DIRS) | set(self.config.get("sensitive_dirs", []))
+        self.exclude_dirs: set[str] = {_to_abs(self.project_root, v) for v in raw_exclude}
+        self.sensitive_dirs: set[str] = {_to_abs(self.project_root, v) for v in raw_sensitive}
+
+        # Лимит обрабатываемых файлов (для отладки)
+        self.limit_files: Optional[int] = self.config.get("limit_files")
+
+        # Диагностика сканирования
+        self.debug_scan: bool = bool(self.config.get("debug_scan", True))
+
+        # Багфиксер
+        self.bugfixer = AIBugFixer(self.chatgpt, max_fix_cycles=self.max_fix_cycles)
+
+    # ───────────────────────── публичный API ─────────────────────────
+
+    def run_self_improvement(self) -> Generator[str, None, None]:
+        """Совместимость со старым интерфейсом."""
+        yield from self.run_project_improvement()
+
+    def run_project_improvement(
+        self,
+        root: str = DEFAULT_ROOT,
+        *,
+        auto_bugfix: Optional[bool] = None,
+        max_fix_cycles: Optional[int] = None,
+        auto_apply_patches: Optional[bool] = None,
+        include_exts: Optional[Iterable[str]] = None,
+        exclude_dirs: Optional[Iterable[str]] = None,
+        sensitive_dirs: Optional[Iterable[str]] = None,
+        limit_files: Optional[int] = None,
+        debug_preview_count: int = 10,
+    ) -> Generator[str, None, None]:
+
+        auto_bugfix = self.auto_bugfix if auto_bugfix is None else bool(auto_bugfix)
+        max_fix_cycles = self.max_fix_cycles if max_fix_cycles is None else int(max_fix_cycles)
+        auto_apply_patches = self.auto_apply_patches if auto_apply_patches is None else bool(auto_apply_patches)
+        include_exts = tuple(include_exts or self.include_exts)
+
+        # если пользователь передал свои фильтры — тоже нормализуем
+        exclude_dirs_set = self.exclude_dirs if exclude_dirs is None else {_to_abs(self.project_root, v) for v in exclude_dirs}
+        sensitive_dirs_set = self.sensitive_dirs if sensitive_dirs is None else {_to_abs(self.project_root, v) for v in sensitive_dirs}
+        limit_files = self.limit_files if (limit_files is None) else limit_files
+        if isinstance(limit_files, bool):
+            limit_files = None
+        if isinstance(limit_files, int) and limit_files <= 0:
+            limit_files = None
+
+        # шапка
+        header = (
+            "🧠 ▶️ Запущен процесс самоусовершенствования Aideon...\n"
+            f"⚙️ Параметры: auto_bugfix={auto_bugfix}, max_fix_cycles={max_fix_cycles}, "
+            f"auto_apply_patches={auto_apply_patches}, backups={self.backup_path}, diffs={self.diff_path}\n"
+            f"📁 project_root={self.project_root}\n"
+            f"🎯 include_exts={list(include_exts)}\n"
+            f"🚧 exclude_dirs(normalized)={sorted(exclude_dirs_set)}\n"
+            f"🛡️ sensitive_dirs(normalized)={sorted(sensitive_dirs_set)}"
+        )
+        log_info(header.replace("\n", " | "))
+        for line in header.split("\n"):
+            if line:
+                yield line
+
+        # 1) Скан проекта (метаданные/кэш — для правой панели)
+        scanner_root = os.path.abspath(os.path.join(self.project_root, root))
+        yield f"🔎 scanner_root={scanner_root}"
+        log_info(f"scanner_root={scanner_root}")
+
+        yield "🔍 Сканирую проект (ProjectScanner.scan)…"
+        try:
+            _ = ProjectScanner(root_path=scanner_root).scan()
+        except Exception as e:
+            log_error(f"Скан провалился: {e}")
+            yield f"💥 Ошибка сканера: {e}"
+            return
+        yield "✅ Сканирование завершено."
+
+        # 2) Сбор кандидатов с диагностикой
+        candidates, stats = self._collect_candidates_with_debug(
+            root=root,
+            include_exts=include_exts,
+            exclude_abs=exclude_dirs_set,
+            sensitive_abs=sensitive_dirs_set,
+        )
+        total_scanned = stats["scanned_files"]
+        included = len(candidates)
+
+        if limit_files:
+            candidates = candidates[: int(limit_files)]
+        chosen = len(candidates)
+
+        diag = (
+            f"🧮 Диагностика отбора: scanned={total_scanned}, "
+            f"excluded_by_ext={stats['excluded_by_ext']}, "
+            f"excluded_by_exclude={stats['excluded_by_exclude']}, "
+            f"excluded_by_sensitive={stats['excluded_by_sensitive']}, "
+            f"included={included}"
+        )
+        log_info(diag); yield diag
+        if limit_files:
+            lim_msg = f"🔢 Ограничение limit_files={limit_files} → к обработке: {chosen}"
+            log_info(lim_msg); yield lim_msg
+
+        # превью кандидатов
+        if candidates:
+            preview = [ _nice_rel(p, self.project_root) for p in candidates[:max(1, debug_preview_count)] ]
+            msg = f"👀 Превью первых {min(debug_preview_count, len(candidates))} файлов: " + ", ".join(preview)
+            log_info(msg); yield msg
+        else:
+            yield "ℹ️ Подходящих файлов не найдено. Ослабь фильтры (exclude/sensitive) или расширь include_exts."
+            return
@@ -53,2 +210,0 @@ class SelfImprover:
-        scanner = ProjectScanner(root_path="app")
-        structure = scanner.scan()
@@ -55,0 +212 @@ class SelfImprover:
+        processed = 0
@@ -57 +214,2 @@ class SelfImprover:
-        for rel_dir, files in structure.items():
+        # 3) Обработка каждого файла
+        for abs_path in candidates:
@@ -64,17 +222,2 @@ class SelfImprover:
-            for file_entry in files:
-                if self.stop_requested:
-                    msg = "⏹️ Остановлено пользователем."
-                    log_warning(msg)
-                    yield msg
-                    break
-
-                fname = file_entry["name"]
-                full_path = os.path.join("app", rel_dir, fname)
-                abs_path = os.path.abspath(full_path)
-
-                old_code = self.file_manager.read_file(abs_path)
-                if not old_code:
-                    msg = f"⚠️ Пропущен файл (не читается): {full_path}"
-                    log_warning(msg)
-                    yield msg
-                    continue
+            rel_path = _nice_rel(abs_path, self.project_root)
+            yield f"— ▶️ Работаю с файлом: {rel_path}"
@@ -82,5 +225,7 @@ class SelfImprover:
-                # Шаг 1 — метасаммери
-                summary = self.summarizer.summarize(full_path, old_code)
-                msg = f"📄 Саммери: {full_path}\n{summary}"
-                log_info(msg)
-                yield msg
+            # чтение исходника
+            try:
+                old_code = self.file_manager.read_text(abs_path)
+            except Exception as e:
+                log_warning(f"[SelfImprover] Не удалось прочитать файл {rel_path}: {e}")
+                yield f"⚠️ Пропущен файл (не читается): {rel_path}"
+                continue
@@ -88,13 +233 @@ class SelfImprover:
-                # Шаг 2 — план улучшения (строим промт для GPT)
-                prompt_plan = self.planner.build_prompt(full_path, summary)
-                if self.chat_panel:
-                    self.chat_panel.add_gpt_request(prompt_plan)
-                try:
-                    raw_response = self.chatgpt.chat(prompt_plan)
-                    if self.chat_panel:
-                        self.chat_panel.add_gpt_response(raw_response)
-                except Exception as e:
-                    msg = f"❌ Ошибка при запросе плана улучшения для {full_path}: {e}"
-                    log_error(msg)
-                    yield msg
-                    continue
+            yield f"📥 Прочитан файл ({len(old_code)} симв.)"
@@ -102 +235,9 @@ class SelfImprover:
-                plan_data = self.planner.extract_plan(raw_response)
+            # summary
+            yield "🧾 Генерация метасаммери (FileSummarizer)…"
+            try:
+                summary = self.summarizer.summarize(rel_path, old_code)
+            except Exception as e:
+                log_warning(f"summary failed for {rel_path}: {e}")
+                yield f"⚠️ Пропуск: не удалось сделать summary ({e})"
+                continue
+            yield f"📄 Саммери: {rel_path}\n{summary}"
@@ -104,8 +245,27 @@ class SelfImprover:
-                if not plan_data or not plan_data.get("plan"):
-                    msg = f"❌ GPT не дал валидный план для: {full_path}"
-                    log_error(msg)
-                    yield msg
-                    continue
-                msg = f"💡 План улучшений для {full_path}:\n{plan_data['plan']}"
-                log_info(msg)
-                yield msg
+            # предварительный багфикс
+            if auto_bugfix:
+                yield f"🧪 Предварительный багфикс включен → пытаюсь для {rel_path}"
+
+                def _apply_attempt(new_text: str):
+                    if auto_apply_patches:
+                        self.patcher.confirm_and_apply_patch(abs_path, old_code, new_text)
+                    else:
+                        self.patcher._save_diff(abs_path, old_code, new_text)
+
+                def _on_error(err: Exception, attempt: int):
+                    log_warning(f"bugfix attempt {attempt} failed for {rel_path}: {err}")
+
+                bugfixed = self.bugfixer.iterative_fix_cycle(
+                    file_path=rel_path,
+                    summary=summary,
+                    old_code=old_code,
+                    apply_callback=_apply_attempt,
+                    on_error_callback=_on_error
+                )
+                if bugfixed and bugfixed != old_code:
+                    yield "✅ Bugfix-патч подготовлен " + ("(applied)" if auto_apply_patches else "(diff сохранён)")
+                    old_code = bugfixed
+                else:
+                    yield "ℹ️ Багфикс изменений не предложил."
+            else:
+                yield "🧪 Предварительный багфикс отключён настройками."
@@ -113,2 +273,11 @@ class SelfImprover:
-                # Шаг 3 — патч (запрос нового кода)
-                patch_prompt = self.requester.build_prompt(full_path, old_code, summary, plan_data)
+            # план
+            yield "📝 Формирую промпт плана (ImprovementPlanner)…"
+            plan_prompt = self.planner.build_prompt(rel_path, summary)
+            if self.chat_panel:
+                try:
+                    self.chat_panel.add_gpt_request(plan_prompt)
+                except Exception:
+                    pass
+            try:
+                yield "🤖 Запрашиваю план у OpenAI…"
+                raw_plan = self.chatgpt.chat(plan_prompt, system_msg=self.planner.SYSTEM_MSG)
@@ -116 +285,32 @@ class SelfImprover:
-                    self.chat_panel.add_gpt_request(patch_prompt)
+                    try:
+                        self.chat_panel.add_gpt_response(raw_plan)
+                    except Exception:
+                        pass
+            except Exception as e:
+                yield f"❌ Ошибка при запросе плана: {e}"
+                continue
+
+            plan_data = self.planner.extract_plan(raw_plan)
+            if not plan_data or not plan_data.get("plan"):
+                yield f"❌ GPT не дал валидный план для: {rel_path}"
+                continue
+
+            if isinstance(plan_data["plan"], list):
+                pretty_lines = []
+                for it in plan_data["plan"]:
+                    s = it.get("step")
+                    a = it.get("action")
+                    d = it.get("details")
+                    if s is not None:
+                        pretty_lines.append(f"{s}. {a or ''}{(' — ' + d) if d else ''}")
+                    else:
+                        pretty_lines.append(f"- {a or ''}{(' — ' + d) if d else ''}")
+                plan_pretty = "\n".join(pretty_lines)
+            else:
+                plan_pretty = str(plan_data["plan"])
+            yield f"💡 План улучшений для {rel_path}:\n{plan_pretty}"
+
+            # запрос нового кода
+            yield "🧵 Готовлю промпт для патча (PatchRequester)…"
+            patch_prompt = self.requester.build_prompt(rel_path, old_code, summary, plan_data)
+            if self.chat_panel:
@@ -118,8 +318,15 @@ class SelfImprover:
-                    new_code = self.chatgpt.chat(patch_prompt)
-                    if self.chat_panel:
-                        self.chat_panel.add_gpt_response(new_code)
-                except Exception as e:
-                    msg = f"⚠️ Ошибка при получении патча: {full_path}: {e}"
-                    log_warning(msg)
-                    yield msg
-                    continue
+                    self.chat_panel.add_gpt_request(patch_prompt)
+                except Exception:
+                    pass
+            try:
+                yield "🤖 Запрашиваю новый код у OpenAI…"
+                raw_code = self.chatgpt.chat(patch_prompt, system_msg=self.requester.SYSTEM_MSG)
+                new_code = self.requester.extract_code(raw_code)
+                if self.chat_panel:
+                    try:
+                        self.chat_panel.add_gpt_response(raw_code)
+                    except Exception:
+                        pass
+            except Exception as e:
+                yield f"⚠️ Ошибка при получении патча: {e}"
+                continue
@@ -127,5 +334,5 @@ class SelfImprover:
-                if not new_code or "Ошибка" in new_code:
-                    msg = f"⚠️ Патч не получен от GPT: {full_path}"
-                    log_warning(msg)
-                    yield msg
-                    continue
+            if not new_code or not isinstance(new_code, str):
+                yield "⚠️ Пустой патч — пропускаю."
+                continue
+
+            yield f"📨 Патч получен ({len(new_code)} симв.)."
@@ -133 +340,3 @@ class SelfImprover:
-                # Шаг 4 — применение или автоматическая отладка
+            # синтакс-проверка для .py
+            syntax_ok = True
+            if rel_path.endswith(".py"):
@@ -135,24 +344,43 @@ class SelfImprover:
-                    if self.apply_patches_automatically:
-                        self.patcher.confirm_and_apply_patch(
-                            file_path=abs_path,
-                            old_code=old_code,
-                            new_code=new_code
-                        )
-                        msg = f"✅ Патч успешно применён: {full_path}"
-                        log_info(msg)
-                        yield msg
-                        any_success = True
-                    else:
-                        # Безопасный режим: только сохранить diff, не применяя
-                        self.patcher._save_diff(abs_path, old_code, new_code)
-                        msg = f"📝 Diff сохранён (без применения): {full_path}"
-                        log_info(msg)
-                        yield msg
-                        any_success = True
-
-                except Exception as e:
-                    log_error(f"💥 Ошибка при применении патча: {e}")
-                    fix_code = self.debugger.request_fix(
-                        file_path=full_path,
-                        original_code=new_code,
-                        error_message=str(e)
+                    ast.parse(new_code)
+                except SyntaxError as e:
+                    syntax_ok = False
+                    log_warning(f"syntax error in new code for {rel_path}: {e}")
+
+            # применить / сохранить diff
+            try:
+                if auto_apply_patches and syntax_ok:
+                    self.patcher.confirm_and_apply_patch(abs_path, old_code, new_code)
+                    any_success = True
+                    yield "🧷 Применение патча… (applied)"
+                    yield f"✅ Патч успешно применён: {rel_path}"
+                else:
+                    self.patcher._save_diff(abs_path, old_code, new_code)
+                    any_success = True
+                    yield "🧷 Применение патча… (save diff only)"
+                    yield f"📝 Diff сохранён (без применения): {rel_path}"
+                    if auto_apply_patches and not syntax_ok:
+                        yield "❌ Новый код не прошёл синтакс-проверку — авто-применение отменено."
+            except Exception as e:
+                log_error(f"Ошибка применения патча для {rel_path}: {e}")
+                yield f"💥 Ошибка применения патча: {e}"
+                # Fallback: пробуем исправить автоматически
+                yield "🧯 Пытаюсь авто-исправить через ErrorDebugger/AIBugFixer…"
+                fix_code: Optional[str] = None
+                try:
+                    fix_code = self.debugger.request_fix(rel_path, new_code, str(e))
+                except Exception:
+                    pass
+                if not fix_code and auto_bugfix:
+                    def _apply_attempt2(nc: str):
+                        if auto_apply_patches:
+                            self.patcher.confirm_and_apply_patch(abs_path, old_code, nc)
+                        else:
+                            self.patcher._save_diff(abs_path, old_code, nc)
+                    def _on_error2(err: Exception, attempt: int):
+                        log_warning(f"fallback bugfix attempt {attempt} failed for {rel_path}: {err}")
+                    fix_code = self.bugfixer.iterative_fix_cycle(
+                        file_path=rel_path,
+                        summary=summary,
+                        old_code=old_code,
+                        apply_callback=_apply_attempt2,
+                        on_error_callback=_on_error2
@@ -160,25 +388,4 @@ class SelfImprover:
-                    if fix_code:
-                        msg = f"🛠️ Попытка автоматического исправления кода для: {full_path}"
-                        log_info(msg)
-                        yield msg
-                        try:
-                            if self.apply_patches_automatically:
-                                self.patcher.confirm_and_apply_patch(
-                                    file_path=abs_path,
-                                    old_code=old_code,
-                                    new_code=fix_code
-                                )
-                                msg = f"✅ Исправление успешно применено: {full_path}"
-                                log_info(msg)
-                                yield msg
-                                any_success = True
-                            else:
-                                self.patcher._save_diff(abs_path, old_code, fix_code)
-                                msg = f"📝 Diff исправления сохранён (без применения): {full_path}"
-                                log_info(msg)
-                                yield msg
-                                any_success = True
-                        except Exception as e2:
-                            msg = f"💥 Ошибка при втором применении патча: {e2}"
-                            log_error(msg)
-                            yield msg
+                if fix_code:
+                    any_success = True
+                    if auto_apply_patches:
+                        yield f"✅ Исправление применено: {rel_path}"
@@ -186,3 +393,3 @@ class SelfImprover:
-                        msg = f"💥 Не удалось автоматически исправить: {full_path}"
-                        log_error(msg)
-                        yield msg
+                        yield f"📝 Diff исправления сохранён (без применения): {rel_path}"
+                else:
+                    yield f"💥 Не удалось автоматически исправить: {rel_path}"
@@ -189,0 +397,5 @@ class SelfImprover:
+            processed += 1
+            if processed % HEARTBEAT_EVERY == 0 or processed == chosen:
+                yield f"⏳ Прогресс: {processed}/{chosen}"
+
+        # 4) финальный статус
@@ -197,0 +410,62 @@ class SelfImprover:
+
+    # ───────────────────────── утилиты ─────────────────────────
+
+    def _collect_candidates_with_debug(
+        self,
+        *,
+        root: str,
+        include_exts: Iterable[str],
+        exclude_abs: set[str],
+        sensitive_abs: set[str],
+    ) -> Tuple[List[str], Dict[str, int]]:
+        """
+        Возвращает (кандидаты, статистика отбора).
+        Исключения проверяются как по абсолютному совпадению корня каталога, так и по префиксу поддерева.
+        """
+        base = os.path.abspath(os.path.join(self.project_root, root))
+        result: List[str] = []
+        stats = {
+            "scanned_files": 0,
+            "excluded_by_ext": 0,
+            "excluded_by_exclude": 0,
+            "excluded_by_sensitive": 0,
+        }
+
+        def _is_under(any_abs_dir: str, path_abs: str) -> bool:
+            any_abs_dir = os.path.normpath(any_abs_dir)
+            path_abs = os.path.normpath(path_abs)
+            return path_abs == any_abs_dir or path_abs.startswith(any_abs_dir + os.sep)
+
+        for dirpath, dirnames, filenames in os.walk(base):
+            # режем обход сразу, чтобы не спускаться в отфильтрованные директории
+            pruned: List[str] = []
+            for d in list(dirnames):
+                abs_dir = os.path.normpath(os.path.join(dirpath, d))
+                if abs_dir in exclude_abs or any(_is_under(ex, abs_dir) for ex in exclude_abs):
+                    pruned.append(d); continue
+                if abs_dir in sensitive_abs or any(_is_under(sx, abs_dir) for sx in sensitive_abs):
+                    pruned.append(d); continue
+            for d in pruned:
+                if d in dirnames:
+                    dirnames.remove(d)
+
+            # файлы
+            for fn in filenames:
+                abs_file = os.path.normpath(os.path.join(dirpath, fn))
+                stats["scanned_files"] += 1
+
+                if not fn.endswith(tuple(include_exts)):
+                    stats["excluded_by_ext"] += 1
+                    continue
+                if any(_is_under(ex, abs_file) for ex in exclude_abs):
+                    stats["excluded_by_exclude"] += 1
+                    continue
+                if any(_is_under(sx, abs_file) for sx in sensitive_abs):
+                    stats["excluded_by_sensitive"] += 1
+                    continue
+
+                result.append(abs_file)
+
+        # стабильно: ближе к корню раньше → удобнее читать диффы
+        result.sort(key=lambda p: (_nice_rel(p, self.project_root).count(os.sep), p.lower()))
+        return result, stats
\ No newline at end of file
```

</details>

<details><summary>"app/modules/self_improver\302\240\342\200\224 \320\272\320\276\320\277\320\270\321\217.py"</summary>

_No textual diff (binary or rename)._

</details>

<details><summary>app/modules/utils.py</summary>

```diff
diff --git a/app/modules/utils.py b/app/modules/utils.py
index 2aee949..0a81857 100644
--- a/app/modules/utils.py
+++ b/app/modules/utils.py
@@ -4 +4,2 @@
-Вспомогательные функции: чтение ключа, копирование файлов, парсинг, и т.д.
+Вспомогательные функции: загрузка API-ключа, модели, параметров генерации.
+Поддерживает ENV и config, есть дефолты.
@@ -7,0 +9 @@ import os
+from typing import Any, Dict, Optional, Union
@@ -9 +11,7 @@ import os
-def load_api_key(config):
+
+def load_param(
+    name: str,
+    env_name: str,
+    config: Optional[Dict[str, Any]],
+    default: Union[str, float, int]
+) -> Union[str, float, int]:
@@ -11,3 +19,5 @@ def load_api_key(config):
-    Вытаскиваем API-ключ из:
-    1) config['openai_api_key']
-    2) переменной окружения OPENAI_API_KEY
+    Универсальная загрузка параметров.
+    Приоритет:
+    1. Переменная окружения (env_name)
+    2. config[name]
+    3. default
@@ -15,4 +25,29 @@ def load_api_key(config):
-    key = config.get("openai_api_key", None)
-    if not key:
-        key = os.environ.get("OPENAI_API_KEY", "")
-    return key
\ No newline at end of file
+    env_val = os.getenv(env_name)
+    if env_val is not None:
+        # Если дефолт — число, пробуем преобразовать
+        if isinstance(default, (float, int)):
+            try:
+                return type(default)(env_val)
+            except (ValueError, TypeError):
+                return default
+        return env_val.strip()
+
+    if config and name in config:
+        return config[name]
+
+    return default
+
+
+def load_api_key(config: Optional[Dict[str, Any]] = None) -> str:
+    """Загрузить API-ключ OpenAI."""
+    return str(load_param("openai_api_key", "OPENAI_API_KEY", config, ""))
+
+
+def load_model_name(config: Optional[Dict[str, Any]] = None) -> str:
+    """Загрузить название модели (по умолчанию gpt-4o)."""
+    return str(load_param("model_name", "OPENAI_MODEL", config, "gpt-4o"))
+
+
+def load_temperature(config: Optional[Dict[str, Any]] = None) -> float:
+    """Загрузить температуру генерации (по умолчанию 0.7)."""
+    return float(load_param("temperature", "OPENAI_TEMPERATURE", config, 0.7))
\ No newline at end of file
```

</details>

<details><summary>app/skills/__init__.py</summary>

```diff
diff --git a/app/skills/__init__.py b/app/skills/__init__.py
new file mode 100644
index 0000000..587bb47
--- /dev/null
+++ b/app/skills/__init__.py
@@ -0,0 +1 @@
+# маркер пакета
\ No newline at end of file
```

</details>

<details><summary>app/skills/fs_read/manifest.json</summary>

```diff
diff --git a/app/skills/fs_read/manifest.json b/app/skills/fs_read/manifest.json
new file mode 100644
index 0000000..c9bdc4a
--- /dev/null
+++ b/app/skills/fs_read/manifest.json
@@ -0,0 +1,6 @@
+{
+  "name": "fs.read",
+  "description": "Читает текстовый файл с диска",
+  "permissions": ["fs.read"],
+  "inputs": { "path": "str" }
+}
\ No newline at end of file
```

</details>

<details><summary>app/skills/fs_read/skill.py</summary>

```diff
diff --git a/app/skills/fs_read/skill.py b/app/skills/fs_read/skill.py
new file mode 100644
index 0000000..ea30c9d
--- /dev/null
+++ b/app/skills/fs_read/skill.py
@@ -0,0 +1,19 @@
+from __future__ import annotations
+from typing import Optional
+import os
+
+from app.core.file_manager import FileManager
+from app.logger import log_info, log_warning
+
+def run(path: str) -> str:
+    """
+    Читать файл безопасно (только текст).
+    """
+    fm = FileManager()
+    abs_path = os.path.abspath(path)
+    text: Optional[str] = fm.read_file(abs_path)
+    if text is None:
+        log_warning(f"[fs.read] не удалось прочитать: {abs_path}")
+        return ""
+    log_info(f"[fs.read] {abs_path} ({len(text)} симв.)")
+    return text
\ No newline at end of file
```

</details>

<details><summary>app/skills/fs_write/manifest.json</summary>

```diff
diff --git a/app/skills/fs_write/manifest.json b/app/skills/fs_write/manifest.json
new file mode 100644
index 0000000..580b6b2
--- /dev/null
+++ b/app/skills/fs_write/manifest.json
@@ -0,0 +1,6 @@
+{
+  "name": "fs.write",
+  "description": "Пишет файл на диск (с диффом). По умолчанию dry-run: только diff.",
+  "permissions": ["fs.write"],
+  "inputs": { "path": "str", "new_text": "str", "apply": "bool" }
+}
\ No newline at end of file
```

</details>

<details><summary>app/skills/fs_write/skill.py</summary>

```diff
diff --git a/app/skills/fs_write/skill.py b/app/skills/fs_write/skill.py
new file mode 100644
index 0000000..27a4f8e
--- /dev/null
+++ b/app/skills/fs_write/skill.py
@@ -0,0 +1,33 @@
+from __future__ import annotations
+import os
+from typing import Optional, Dict, Any
+
+from app.core.file_manager import FileManager
+from app.modules.improver.patcher import CodePatcher
+from app.logger import log_info
+
+def run(path: str, new_text: str, apply: bool = False) -> Dict[str, Any]:
+    """
+    По умолчанию — сохраняет только diff (apply=False).
+    Если apply=True — перезаписывает файл, создает бэкап и diff.
+    """
+    fm = FileManager()
+    cp = CodePatcher()
+    abs_path = os.path.abspath(path)
+    old_text: Optional[str] = fm.read_file(abs_path) or ""
+
+    if not apply:
+        # безопасный режим: только diff
+        diff_path = cp._save_diff(abs_path, old_text, new_text)
+        return {"mode": "diff-only", "diff_path": diff_path}
+
+    # запись с бэкапом и diff
+    backup_path, diff_path = cp.apply_patch_no_prompt(
+        file_path=abs_path,
+        old_code=old_text,
+        new_code=new_text,
+        save_backup=True,
+        save_diff=True
+    )
+    log_info(f"[fs.write] применено apply=True path={abs_path}")
+    return {"mode": "apply", "backup_path": backup_path, "diff_path": diff_path}
\ No newline at end of file
```

</details>

<details><summary>app/skills/http_get/manifest.json</summary>

```diff
diff --git a/app/skills/http_get/manifest.json b/app/skills/http_get/manifest.json
new file mode 100644
index 0000000..f468456
--- /dev/null
+++ b/app/skills/http_get/manifest.json
@@ -0,0 +1,6 @@
+{
+  "name": "http.get",
+  "description": "Простой GET-запрос (если политика разрешает сеть).",
+  "permissions": ["net.out"],
+  "inputs": { "url": "str", "timeout": "int" }
+}
\ No newline at end of file
```

</details>

<details><summary>app/skills/http_get/skill.py</summary>

```diff
diff --git a/app/skills/http_get/skill.py b/app/skills/http_get/skill.py
new file mode 100644
index 0000000..883c6d3
--- /dev/null
+++ b/app/skills/http_get/skill.py
@@ -0,0 +1,22 @@
+from __future__ import annotations
+from typing import Dict, Any
+import json
+
+try:
+    import requests  # опционально
+except Exception:
+    requests = None  # type: ignore
+
+from app.logger import log_warning
+
+def run(url: str, timeout: int = 10) -> Dict[str, Any]:
+    if requests is None:
+        log_warning("[http.get] модуль requests не установлен")
+        return {"ok": False, "error": "requests not installed"}
+    try:
+        r = requests.get(url, timeout=timeout)
+        # не возвращаем гигантские тела
+        body = r.text[:10000]
+        return {"ok": True, "status": r.status_code, "body": body}
+    except Exception as e:
+        return {"ok": False, "error": str(e)}
\ No newline at end of file
```

</details>

<details><summary>app/skills/logger.py</summary>

```diff
diff --git a/app/skills/logger.py b/app/skills/logger.py
new file mode 100644
index 0000000..46b7e5e
--- /dev/null
+++ b/app/skills/logger.py
@@ -0,0 +1,106 @@
+# app/logger.py
+from __future__ import annotations
+
+import os
+import logging
+from typing import Optional
+from logging.handlers import RotatingFileHandler
+
+# ---------- Константы и пути ----------
+DEFAULT_LOG_DIR = os.getenv("LOG_DIR", "app/logs")
+MAIN_LOG_FILE = "aideon.log"
+
+# ---------- Цветной форматтер для консоли ----------
+class ColorFormatter(logging.Formatter):
+    COLORS = {
+        logging.DEBUG: "\033[94m",    # Синий
+        logging.INFO: "\033[92m",     # Зеленый
+        logging.WARNING: "\033[93m",  # Желтый
+        logging.ERROR: "\033[91m",    # Красный
+        logging.CRITICAL: "\033[95m", # Фиолетовый
+    }
+    RESET = "\033[0m"
+
+    def format(self, record: logging.LogRecord) -> str:
+        color = self.COLORS.get(record.levelno, "")
+        base = super().format(record)
+        return f"{color}{base}{self.RESET}"
+
+# ---------- Глобальный синглтон логгера ----------
+_LOGGER: Optional[logging.Logger] = None
+
+def setup_logging() -> logging.Logger:
+    """
+    Инициализация логирования:
+      - уровень берём из ENV LOG_LEVEL (DEBUG/INFO/WARNING/ERROR), по умолчанию INFO
+      - вывод в консоль (цветной)
+      - вывод в файл app/logs/aideon.log (ротация 2MB x 3)
+      - отдельные файлы info.log / warning.log / error.log
+    Повторный вызов безопасен (хендлеры не дублируются).
+    """
+    global _LOGGER
+    if _LOGGER is not None:
+        return _LOGGER
+
+    os.makedirs(DEFAULT_LOG_DIR, exist_ok=True)
+
+    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
+    level = getattr(logging, level_name, logging.INFO)
+
+    logger = logging.getLogger("Aideon")
+    logger.setLevel(level)
+    logger.propagate = False  # чтобы не улетало в корневой логгер
+
+    # Форматы
+    fmt = "%(asctime)s | %(levelname)s | %(message)s"
+    datefmt = "%Y-%m-%d %H:%M:%S"
+    formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)
+    color_formatter = ColorFormatter(fmt=fmt, datefmt=datefmt)
+
+    # Проверка на наличие хендлеров — чтобы не дублировать
+    if not logger.handlers:
+        # Консоль
+        sh = logging.StreamHandler()
+        sh.setLevel(level)
+        sh.setFormatter(color_formatter)
+        logger.addHandler(sh)
+
+        # Главный файл (ротация)
+        main_path = os.path.join(DEFAULT_LOG_DIR, MAIN_LOG_FILE)
+        fh = RotatingFileHandler(main_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8")
+        fh.setLevel(level)
+        fh.setFormatter(formatter)
+        logger.addHandler(fh)
+
+        # Отдельные файлы по уровням
+        per_level = [
+            (logging.INFO,    "info.log"),
+            (logging.WARNING, "warning.log"),
+            (logging.ERROR,   "error.log"),
+        ]
+        for lvl, fname in per_level:
+            path = os.path.join(DEFAULT_LOG_DIR, fname)
+            h = logging.FileHandler(path, encoding="utf-8")
+            h.setLevel(lvl)
+            h.setFormatter(formatter)
+            logger.addHandler(h)
+
+    _LOGGER = logger
+    logger.debug("Логирование инициализировано (level=%s, dir=%s)", level_name, DEFAULT_LOG_DIR)
+    return logger
+
+def _get_logger() -> logging.Logger:
+    return _LOGGER or setup_logging()
+
+# ---------- Упрощённые функции (совместимость с существующим кодом) ----------
+def log_debug(msg: str) -> None:
+    _get_logger().debug(msg)
+
+def log_info(msg: str) -> None:
+    _get_logger().info(msg)
+
+def log_warning(msg: str) -> None:
+    _get_logger().warning(msg)
+
+def log_error(msg: str) -> None:
+    _get_logger().error(msg)
\ No newline at end of file
```

</details>

<details><summary>app/skills/shell_exec/manifest.json</summary>

```diff
diff --git a/app/skills/shell_exec/manifest.json b/app/skills/shell_exec/manifest.json
new file mode 100644
index 0000000..2265e9b
--- /dev/null
+++ b/app/skills/shell_exec/manifest.json
@@ -0,0 +1,6 @@
+{
+  "name": "proc.shell",
+  "description": "Выполнить shell-команду (обычно заблокировано политикой).",
+  "permissions": ["proc.shell"],
+  "inputs": { "cmd": "str" }
+}
\ No newline at end of file
```

</details>

<details><summary>app/skills/shell_exec/skill.py</summary>

```diff
diff --git a/app/skills/shell_exec/skill.py b/app/skills/shell_exec/skill.py
new file mode 100644
index 0000000..2909401
--- /dev/null
+++ b/app/skills/shell_exec/skill.py
@@ -0,0 +1,11 @@
+from __future__ import annotations
+import subprocess
+from typing import Dict, Any
+
+def run(cmd: str) -> Dict[str, Any]:
+    """
+    Опасный скилл — как правило блокируется SafetyGuardian по policy.
+    """
+    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
+    out, err = p.communicate(timeout=30)
+    return {"code": p.returncode, "stdout": out[-5000:], "stderr": err[-5000:]}
\ No newline at end of file
```

</details>

<details><summary>app/ui/main_window.py</summary>

```diff
diff --git a/app/ui/main_window.py b/app/ui/main_window.py
index 7bb9b94..fa370ea 100644
--- a/app/ui/main_window.py
+++ b/app/ui/main_window.py
@@ -0,0 +1,2 @@
+from __future__ import annotations
+
@@ -1,0 +4 @@ import os
+import json
@@ -2,0 +6,2 @@ from datetime import datetime
+from typing import Optional, List, Dict, Any
+
@@ -5 +10,2 @@ from PyQt6.QtWidgets import (
-    QPushButton, QTextEdit, QHBoxLayout, QLabel, QSplitter, QTabWidget, QInputDialog, QMessageBox
+    QPushButton, QTextEdit, QHBoxLayout, QLabel, QSplitter, QTabWidget,
+    QInputDialog, QMessageBox, QToolBar
@@ -14,0 +21,26 @@ from app.modules.analyzer import CodeAnalyzer
+# безопасные геттеры параметров
+from app.modules.utils import load_api_key, load_model_name, load_temperature
+
+# ----- Агент и его совместимые зависимости (мягкие импорты) -----
+try:
+    from app.agent.agent import AideonAgent  # type: ignore
+except Exception:
+    AideonAgent = None  # type: ignore
+
+try:
+    from app.agent.bridge_self_improver import SelfImproverBridge  # type: ignore
+except Exception:
+    SelfImproverBridge = None  # type: ignore
+
+try:
+    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
+except Exception:
+    FileManager = None  # type: ignore
+    FileManagerConfig = None  # type: ignore
+
+try:
+    from app.modules.improver.patcher import CodePatcher  # type: ignore
+except Exception:
+    CodePatcher = None  # type: ignore
+
+
@@ -17,2 +49,2 @@ class SelfImproverPanel(QWidget):
-    Правая панель: модуль саморазвития (SelfImprover) — ручной режим + стоп + метасаммери +
-    вкладки: идеи AI, история изменений, задачи/запросы.
+    Правая панель: модуль саморазвития (SelfImprover).
+    Вкладки: процесс, метасаммери, AI-идеи, история, задачи.
@@ -20 +52 @@ class SelfImproverPanel(QWidget):
-    def __init__(self, config, chat_panel=None, parent=None):
+    def __init__(self, config: Dict[str, Any], chat_panel: Optional[ChatPanel] = None, parent: Optional[QWidget] = None):
@@ -22 +54 @@ class SelfImproverPanel(QWidget):
-        self.config = config
+        self.config = dict(config or {})
@@ -24 +56,2 @@ class SelfImproverPanel(QWidget):
-        self.improver = SelfImprover(config, chat_panel=chat_panel)
+        self.improver = SelfImprover(self.config, chat_panel=chat_panel)
+
@@ -27 +59,0 @@ class SelfImproverPanel(QWidget):
-        self._init_ui()
@@ -29 +61,2 @@ class SelfImproverPanel(QWidget):
-        self.code_analyzer = CodeAnalyzer(config)
+        # Инструменты
+        self.code_analyzer = CodeAnalyzer(self.config)
@@ -31 +64,6 @@ class SelfImproverPanel(QWidget):
-        self.meta_summary_cache = None
+        self.meta_summary_cache: Optional[Dict[str, Any]] = None
+
+        # Данные для вкладок
+        self.ai_ideas: List[str] = []
+        self.history: List[str] = []
+        self.tasks: List[str] = []
@@ -33,6 +71,3 @@ class SelfImproverPanel(QWidget):
-        # Для вкладки AI-идей
-        self.ai_ideas = []
-        # Для истории изменений
-        self.history = []
-        # Для задач
-        self.tasks = []
+        self._init_ui()
+
+    # ---------- UI ----------
@@ -42 +76,0 @@ class SelfImproverPanel(QWidget):
-
@@ -45,31 +79,10 @@ class SelfImproverPanel(QWidget):
-        # Логи процесса улучшения
-        self.log_output = QTextEdit()
-        self.log_output.setReadOnly(True)
-        self.log_output.setStyleSheet("background-color: #f9f9f9; font-family: monospace;")
-        self.tabs.addTab(self.log_output, "Процесс улучшения")
-
-        # Метасаммери по проекту
-        self.meta_output = QTextEdit()
-        self.meta_output.setReadOnly(True)
-        self.meta_output.setStyleSheet("background-color: #eef5fa; font-family: monospace;")
-        self.tabs.addTab(self.meta_output, "📊 Метасаммери проекта")
-
-        # AI-идеи (экспансия)
-        self.ai_ideas_output = QTextEdit()
-        self.ai_ideas_output.setReadOnly(True)
-        self.ai_ideas_output.setStyleSheet("background-color: #e8faef; font-family: monospace;")
-        self.tabs.addTab(self.ai_ideas_output, "💡 AI-идеи/Экспансия")
-
-        # История изменений
-        self.history_output = QTextEdit()
-        self.history_output.setReadOnly(True)
-        self.history_output.setStyleSheet("background-color: #f5f0e6; font-family: monospace;")
-        self.tabs.addTab(self.history_output, "🕓 История изменений")
-
-        # Запросы/Задачи
-        self.tasks_output = QTextEdit()
-        self.tasks_output.setReadOnly(True)
-        self.tasks_output.setStyleSheet("background-color: #f4eaff; font-family: monospace;")
-        self.tabs.addTab(self.tasks_output, "📝 Запросы/Задачи")
-
-        layout.addWidget(QLabel("🤖 Саморазвитие Aideon"))
+        # Логи/вкладки
+        self.log_output = self._make_tab("Процесс улучшения", "#f9f9f9")
+        self.meta_output = self._make_tab("📊 Метасаммери проекта", "#eef5fa")
+        self.ai_ideas_output = self._make_tab("💡 AI-идеи/Экспансия", "#e8faef")
+        self.history_output = self._make_tab("🕓 История изменений", "#f5f0e6")
+        self.tasks_output = self._make_tab("📝 Запросы/Задачи", "#f4eaff")
+
+        header = QLabel("🤖 Саморазвитие Aideon")
+        header.setStyleSheet("font-weight: 600;")
+        layout.addWidget(header)
@@ -77,0 +91 @@ class SelfImproverPanel(QWidget):
+        # Кнопки
@@ -115,0 +130,9 @@ class SelfImproverPanel(QWidget):
+    def _make_tab(self, title: str, bg: str) -> QTextEdit:
+        widget = QTextEdit()
+        widget.setReadOnly(True)
+        widget.setStyleSheet(f"background-color: {bg}; font-family: monospace;")
+        self.tabs.addTab(widget, title)
+        return widget
+
+    # ---------- Логика ----------
+
@@ -119 +142,6 @@ class SelfImproverPanel(QWidget):
-        self.generator = self.improver.run_self_improvement()
+        try:
+            self.generator = self.improver.run_self_improvement()
+        except Exception as e:
+            self.log_output.append(f"❌ Не удалось запустить процесс: {e}\n")
+            self.reset_buttons()
+            return
@@ -133,4 +161,7 @@ class SelfImproverPanel(QWidget):
-            self.log_output.append(step)
-            self.history.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {step}")
-            self.update_history_tab()
-            if "завершено" in step or "Завершено" in step:
+            if step:
+                if not step.endswith("\n"):
+                    step += "\n"
+                self.log_output.append(step)
+                self.history.append(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {step.strip()}")
+                self.update_history_tab()
+            if step and ("завершено" in step.lower()):
@@ -142 +173,4 @@ class SelfImproverPanel(QWidget):
-            self.log_output.append("⚠️ Ошибка: попытка повторного шага до завершения предыдущего.\n")
+            self.log_output.append("⚠️ Ошибка: повторный шаг до завершения предыдущего.\n")
+            self.reset_buttons()
+        except Exception as e:
+            self.log_output.append(f"💥 Исключение в шаге: {e}\n")
@@ -150 +183,0 @@ class SelfImproverPanel(QWidget):
-        # Передаём в модуль признак остановки
@@ -155 +188 @@ class SelfImproverPanel(QWidget):
-        self.log_output.append("🛑 Самоулучшение остановлено пользователем.\n")
+        self.log_output.append("🛑 Самоулучшение остановлено.\n")
@@ -163,0 +197,2 @@ class SelfImproverPanel(QWidget):
+    # ---------- Метасаммери ----------
+
@@ -165,3 +199,0 @@ class SelfImproverPanel(QWidget):
-        """
-        Формирует и выводит метасаммери по всем .py файлам проекта.
-        """
@@ -170,3 +202,6 @@ class SelfImproverPanel(QWidget):
-        self.meta_output.append("📊 <b>Метасаммери по всем файлам проекта:</b>\n")
-        scanner = self.project_scanner
-        tree = scanner.scan()
+        self.meta_output.append("📊 <b>Метасаммери по всем файлам:</b>\n")
+        try:
+            tree = self.project_scanner.scan()
+        except Exception as e:
+            self.meta_output.append(f"❌ Ошибка сканера проекта: {e}\n")
+            return
@@ -173,0 +209 @@ class SelfImproverPanel(QWidget):
+        import pprint
@@ -177,7 +213,9 @@ class SelfImproverPanel(QWidget):
-                summary = f['summary']
-                if isinstance(summary, dict):
-                    import pprint
-                    summary_str = pprint.pformat(summary, compact=True, width=100)
-                else:
-                    summary_str = str(summary)
-                self.meta_output.append(f"\n<b>{f['name']}</b>:\n{summary_str}\n{'-'*50}")
+                summary = f.get("summary")
+                summary_str = (
+                    pprint.pformat(summary, compact=True, width=100)
+                    if isinstance(summary, dict) else str(summary)
+                )
+                name = f.get("name", "unknown")
+                self.meta_output.append(f"\n<b>{name}</b>:\n{summary_str}\n{'-'*50}")
+
+    # ---------- Идеи ----------
@@ -186 +224 @@ class SelfImproverPanel(QWidget):
-        idea, ok = QInputDialog.getText(self, "Добавить AI-идею", "Опишите идею/фичу для AI:")
+        idea, ok = QInputDialog.getText(self, "Добавить AI-идею", "Опишите идею:")
@@ -193,4 +230,0 @@ class SelfImproverPanel(QWidget):
-        """
-        Генерирует идею на основе текущих summary и отправляет её в AI-идеи.
-        """
-        # Используем кэш, если уже строили метасаммери
@@ -198,0 +233,3 @@ class SelfImproverPanel(QWidget):
+        text_summary = "\n".join(
+            f"{f.get('name','?')}: {f.get('summary')}" for _, files in (self.meta_summary_cache or {}).items() for f in files
+        )
@@ -200,3 +237,3 @@ class SelfImproverPanel(QWidget):
-            "Проанализируй следующие summary файлов проекта и предложи одну идею или модуль,"
-            " который значительно усилит, ускорит или расширит возможности системы."
-            "\n\nСписок summary по файлам:\n"
+            "Проанализируй summary файлов проекта и предложи одну идею/модуль "
+            "для усиления или расширения системы:\n\n"
+            f"{text_summary}\n\nОтветь кратко:"
@@ -204,12 +241,10 @@ class SelfImproverPanel(QWidget):
-        text_summary = ""
-        for rel_dir, files in (self.meta_summary_cache or {}).items():
-            for f in files:
-                summary = f['summary']
-                summary_str = summary if isinstance(summary, str) else str(summary)
-                text_summary += f"{f['name']}: {summary_str}\n"
-        prompt += text_summary + "\n\nОтветь кратко, одна идея:"
-        idea = self.code_analyzer.chat(prompt, system_msg="Ты — архитектор новых AI-модулей.")
-        entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
-        self.ai_ideas.append(entry)
-        self.update_ai_ideas_tab()
-        QMessageBox.information(self, "AI-идея получена", f"AI-идея:\n{idea.strip()}")
+        try:
+            idea = self.code_analyzer.chat(prompt, system_msg="Ты — архитектор AI-модулей.")
+        except Exception as e:
+            QMessageBox.warning(self, "Ошибка AI", f"Не удалось сгенерировать идею: {e}")
+            return
+        if idea:
+            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {idea.strip()}"
+            self.ai_ideas.append(entry)
+            self.update_ai_ideas_tab()
+            QMessageBox.information(self, "AI-идея", f"AI-идея:\n{idea.strip()}")
@@ -219 +254 @@ class SelfImproverPanel(QWidget):
-        self.ai_ideas_output.append("💡 <b>AI-идеи/экспансия (ручные и AI-подсказки):</b>\n")
+        self.ai_ideas_output.append("💡 <b>AI-идеи:</b>\n")
@@ -222,0 +258,2 @@ class SelfImproverPanel(QWidget):
+    # ---------- Задачи ----------
+
@@ -224 +261 @@ class SelfImproverPanel(QWidget):
-        task, ok = QInputDialog.getText(self, "Добавить задачу/запрос", "Опишите задачу для AI:")
+        task, ok = QInputDialog.getText(self, "Добавить задачу", "Опишите задачу:")
@@ -231,3 +267,0 @@ class SelfImproverPanel(QWidget):
-        """
-        Генерирует рекомендацию по доработке/задачу для AI на основе summary.
-        """
@@ -235,0 +270,3 @@ class SelfImproverPanel(QWidget):
+        text_summary = "\n".join(
+            f"{f.get('name','?')}: {f.get('summary')}" for _, files in (self.meta_summary_cache or {}).items() for f in files
+        )
@@ -237,3 +274,3 @@ class SelfImproverPanel(QWidget):
-            "Посмотри на summary файлов и сформулируй одну актуальную задачу для развития проекта — "
-            "что можно улучшить или внедрить первым делом:"
-            "\n\nСписок summary по файлам:\n"
+            "Посмотри на summary файлов и предложи одну актуальную задачу "
+            "для развития проекта:\n\n"
+            f"{text_summary}\n\nОтветь кратко:"
@@ -241,12 +278,10 @@ class SelfImproverPanel(QWidget):
-        text_summary = ""
-        for rel_dir, files in (self.meta_summary_cache or {}).items():
-            for f in files:
-                summary = f['summary']
-                summary_str = summary if isinstance(summary, str) else str(summary)
-                text_summary += f"{f['name']}: {summary_str}\n"
-        prompt += text_summary + "\n\nОтветь кратко, одна задача:"
-        task = self.code_analyzer.chat(prompt, system_msg="Ты — AI-продукт менеджер.")
-        entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
-        self.tasks.append(entry)
-        self.update_tasks_tab()
-        QMessageBox.information(self, "AI-задача получена", f"AI-задача:\n{task.strip()}")
+        try:
+            task = self.code_analyzer.chat(prompt, system_msg="Ты — AI-продукт менеджер.")
+        except Exception as e:
+            QMessageBox.warning(self, "Ошибка AI", f"Не удалось сгенерировать задачу: {e}")
+            return
+        if task:
+            entry = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: {task.strip()}"
+            self.tasks.append(entry)
+            self.update_tasks_tab()
+            QMessageBox.information(self, "AI-задача", f"AI-задача:\n{task.strip()}")
@@ -256 +291 @@ class SelfImproverPanel(QWidget):
-        self.tasks_output.append("📝 <b>Список текущих задач и запросов для AI/пользователя:</b>\n")
+        self.tasks_output.append("📝 <b>Задачи:</b>\n")
@@ -259,0 +295,2 @@ class SelfImproverPanel(QWidget):
+    # ---------- История ----------
+
@@ -262 +299 @@ class SelfImproverPanel(QWidget):
-        self.history_output.append("🕓 <b>История изменений/логов процесса:</b>\n")
+        self.history_output.append("🕓 <b>История изменений:</b>\n")
@@ -265,0 +303 @@ class SelfImproverPanel(QWidget):
+
@@ -267,4 +305,2 @@ class MainWindow(QMainWindow):
-    """
-    Главное окно Aideon 5.0: ChatPanel + расширенная SelfImproverPanel
-    """
-    def __init__(self, config=None):
+    """Главное окно Aideon 5.0"""
+    def __init__(self, config: Optional[Dict[str, Any]] = None, agent: Optional["AideonAgent"] = None):
@@ -272 +308 @@ class MainWindow(QMainWindow):
-        self.config = config or {}
+        self.config = self._load_config(config)
@@ -277,0 +314,4 @@ class MainWindow(QMainWindow):
+        # 🔧 Агент
+        self.agent: Optional["AideonAgent"] = agent
+        self.agent_state: Optional[Dict[str, Any]] = None
+
@@ -279,0 +320,2 @@ class MainWindow(QMainWindow):
+        self.ensure_agent_menu()
+        self._create_agent_toolbar()
@@ -280,0 +323 @@ class MainWindow(QMainWindow):
+        self._update_agent_badge()
@@ -281,0 +325,6 @@ class MainWindow(QMainWindow):
+    # --- публичный setter, если агент создаётся в main.py ---
+    def set_agent(self, agent: Optional["AideonAgent"]) -> None:
+        self.agent = agent
+        self._update_agent_badge()
+
+    # --- меню ---
@@ -285,0 +335 @@ class MainWindow(QMainWindow):
+        # Файл
@@ -290,0 +341,41 @@ class MainWindow(QMainWindow):
+        # Контейнер «Агент»
+        self._agent_menu_ref: Optional[Any] = menubar.addMenu("Агент")
+
+    def ensure_agent_menu(self):
+        """Создаёт/обновляет меню 'Агент'."""
+        if not hasattr(self, "_agent_menu_ref") or self._agent_menu_ref is None:
+            self._agent_menu_ref = self.menuBar().addMenu("Агент")
+        agent_menu = self._agent_menu_ref
+        agent_menu.clear()
+
+        boot_action = QAction("🔎 Инициализировать (capabilities + skills)", self)
+        boot_action.triggered.connect(self._agent_boot)
+        agent_menu.addAction(boot_action)
+
+        plan_action = QAction("📝 Построить план…", self)
+        plan_action.triggered.connect(self._agent_plan_dialog)
+        agent_menu.addAction(plan_action)
+
+        run_action = QAction("▶️ Выполнить цель…", self)
+        run_action.triggered.connect(self._agent_run_dialog)
+        agent_menu.addAction(run_action)
+
+    def _create_agent_toolbar(self):
+        """Тулбар с действиями агента (виден всегда)."""
+        tb = QToolBar("Агент", self)
+        tb.setMovable(False)
+        self.addToolBar(Qt.ToolBarArea.BottomToolBarArea, tb)
+
+        act_boot = QAction("Агент: Инициализировать", self)
+        act_boot.triggered.connect(self._agent_boot)
+        tb.addAction(act_boot)
+
+        act_plan = QAction("Агент: План…", self)
+        act_plan.triggered.connect(self._agent_plan_dialog)
+        tb.addAction(act_plan)
+
+        act_run = QAction("Агент: Выполнить…", self)
+        act_run.triggered.connect(self._agent_run_dialog)
+        tb.addAction(act_run)
+
+    # --- основная раскладка ---
@@ -293 +383,0 @@ class MainWindow(QMainWindow):
-
@@ -295,6 +385 @@ class MainWindow(QMainWindow):
-        self.self_improver_panel = SelfImproverPanel(
-            config=self.config,
-            chat_panel=self.chat_panel,
-            parent=self
-        )
-
+        self.self_improver_panel = SelfImproverPanel(config=self.config, chat_panel=self.chat_panel, parent=self)
@@ -303 +387,0 @@ class MainWindow(QMainWindow):
-
@@ -306 +389,0 @@ class MainWindow(QMainWindow):
-
@@ -311,0 +395 @@ class MainWindow(QMainWindow):
+    # --- settings ---
@@ -314,2 +398 @@ class MainWindow(QMainWindow):
-        geometry = settings.value("geometry")
-        if geometry:
+        if (geometry := settings.value("geometry")):
@@ -317,2 +400 @@ class MainWindow(QMainWindow):
-        window_state = settings.value("windowState")
-        if window_state:
+        if (window_state := settings.value("windowState")):
@@ -328 +410,241 @@ class MainWindow(QMainWindow):
-        super().closeEvent(event)
\ No newline at end of file
+        super().closeEvent(event)
+
+    # ---------- Агент: helpers ----------
+
+    def _ensure_agent(self):
+        """Создаёт агента с максимальной совместимостью конструкторов."""
+        if self.agent is not None:
+            return
+
+        if AideonAgent is None:
+            raise RuntimeError("Модуль агента недоступен (AideonAgent not found).")
+
+        repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
+        policy_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "agent", "policy_default.json"))
+
+        fm = None
+        bridge = None
+        patcher = None
+
+        try:
+            if FileManager and FileManagerConfig:
+                fm_cfg = FileManagerConfig(
+                    base_dir=repo_root,
+                    allowed_roots=[repo_root],
+                    read_only_paths=[os.path.join(repo_root, ".git")],
+                    backups_dirname=".aideon_backups",
+                    create_missing_dirs=True,
+                    atomic_write=True,
+                )
+                fm = FileManager(fm_cfg)
+            if CodePatcher:
+                try:
+                    patcher = CodePatcher(file_manager=fm)  # type: ignore
+                except TypeError:
+                    patcher = CodePatcher()  # type: ignore
+            if SelfImproverBridge:
+                try:
+                    bridge = SelfImproverBridge(file_manager=fm, patcher=patcher)  # type: ignore
+                except TypeError:
+                    try:
+                        bridge = SelfImproverBridge(patcher=patcher)  # type: ignore
+                    except Exception:
+                        bridge = None
+        except Exception:
+            fm = None
+            bridge = None
+            patcher = None
+
+        last_err: Optional[Exception] = None
+        for kwargs in (
+            dict(file_manager=fm, improver_bridge=bridge, policy_path=policy_path, config=self.config),
+            dict(improver_bridge=bridge, policy_path=policy_path, config=self.config),
+            dict(policy_path=policy_path, config=self.config),
+            dict(policy_path=policy_path),
+        ):
+            try:
+                self.agent = AideonAgent(**kwargs)  # type: ignore
+                break
+            except Exception as e:
+                last_err = e
+                self.agent = None
+
+        if self.agent is None and last_err:
+            raise last_err
+
+    def _ensure_agent_boot(self):
+        self._ensure_agent()
+        if not self.agent:
+            return
+        if self.agent_state is None:
+            try:
+                if hasattr(self.agent, "boot"):
+                    self.agent_state = self.agent.boot()  # type: ignore
+                elif hasattr(self.agent, "initialize"):
+                    self.agent_state = self.agent.initialize()  # type: ignore
+                else:
+                    self.agent_state = {}
+            finally:
+                self._update_agent_badge()
+
+    def _append_to_chat(self, text: str):
+        if hasattr(self.chat_panel, "append_assistant"):
+            try:
+                self.chat_panel.append_assistant(text)  # type: ignore
+                return
+            except Exception:
+                pass
+        try:
+            QMessageBox.information(self, "Агент", text)
+        except Exception:
+            pass
+
+    def _update_agent_badge(self):
+        badge = "🧩 Агент: off"
+        if self.agent_state is not None:
+            badge = "🧩 Агент: ready"
+        self.setWindowTitle(f"Aideon 5.0 — {badge}")
+
+    # ---------- Агент: actions ----------
+
+    def _agent_boot(self):
+        try:
+            self._ensure_agent_boot()
+            if self.agent_state is not None:
+                QMessageBox.information(self, "Агент", "Агент инициализирован (capabilities + skills).")
+        except Exception as e:
+            QMessageBox.critical(self, "Агент", f"Ошибка инициализации: {e}")
+
+    def _agent_plan_dialog(self):
+        try:
+            self._ensure_agent_boot()
+            if not self.agent:
+                return
+            goal, ok = QInputDialog.getText(self, "План агента", "Цель (goal):")
+            if not ok or not goal.strip():
+                return
+
+            plan = None
+            err: Optional[Exception] = None
+
+            # 1) Новые API
+            try:
+                if hasattr(self.agent, "plan"):
+                    plan = self.agent.plan(goal)  # type: ignore
+            except Exception as e:
+                err = e
+                plan = None
+
+            # 2) Современный планировщик
+            if plan is None:
+                try:
+                    if hasattr(self.agent, "planner") and hasattr(self.agent.planner, "build_high_level_plan"):
+                        plan = self.agent.planner.build_high_level_plan(goal=goal)  # type: ignore
+                except Exception as e:
+                    err = e
+                    plan = None
+
+            # 3) Совместимость со старым make_plan
+            if plan is None:
+                try:
+                    if hasattr(self.agent, "planner") and hasattr(self.agent.planner, "make_plan"):
+                        state = self.agent_state or {}
+                        plan = self.agent.planner.make_plan([goal], state)  # type: ignore
+                except Exception as e:
+                    err = e
+                    plan = None
+
+            if not plan:
+                msg = "План пуст.\nПроверь policy_default.json или задай более конкретную цель."
+                if err:
+                    msg += f"\nПоследняя ошибка: {err}"
+                QMessageBox.warning(self, "Агент", msg)
+                return
+
+            pretty = json.dumps(plan, ensure_ascii=False, indent=2)
+            self._append_to_chat(f"📝 План для цели:\n{pretty}")
+        except Exception as e:
+            QMessageBox.critical(self, "Агент", f"Ошибка построения плана: {e}")
+
+    def _agent_run_dialog(self):
+        try:
+            self._ensure_agent_boot()
+            if not self.agent:
+                return
+            goal, ok = QInputDialog.getText(self, "Выполнить цель", "Цель (goal):")
+            if not ok or not goal.strip():
+                return
+
+            result = None
+            err: Optional[Exception] = None
+
+            # 1) Современный автономный ран
+            try:
+                if hasattr(self.agent, "run_autonomous"):
+                    result = self.agent.run_autonomous(goal=goal, max_steps=8)  # type: ignore
+            except Exception as e:
+                err = e
+                result = None
+
+            # 2) Старый run_goals
+            if result is None:
+                try:
+                    if hasattr(self.agent, "run_goals"):
+                        result = self.agent.run_goals([goal])  # type: ignore
+                except Exception as e:
+                    err = e
+                    result = None
+
+            # 3) Очень старый execute
+            if result is None:
+                try:
+                    if hasattr(self.agent, "execute"):
+                        result = self.agent.execute(goal)  # type: ignore
+                except Exception as e:
+                    err = e
+                    result = None
+
+            if result is None:
+                msg = "Агент не смог выполнить цель. Смотри app/logs/agent.jsonl и aideon.log."
+                if err:
+                    msg += f"\nПоследняя ошибка: {err}"
+                QMessageBox.critical(self, "Агент", msg)
+                return
+
+            pretty = json.dumps(result, ensure_ascii=False, indent=2)
+            self._append_to_chat(f"▶️ Результат выполнения:\n{pretty}")
+            QMessageBox.information(self, "Агент", "Выполнение завершено. Результат выведен в чат.")
+        except Exception as e:
+            QMessageBox.critical(self, "Агент", f"Ошибка выполнения: {e}")
+
+    # ---------- безопасная загрузка конфига ----------
+
+    def _load_config(self, passed: Optional[Dict[str, Any]]) -> Dict[str, Any]:
+        cfg: Dict[str, Any] = {}
+        if isinstance(passed, dict):
+            cfg.update(passed)
+
+        cfg_path_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "config.json"))
+        cfg = self._merge_json_safely(cfg, cfg_path_root)
+
+        cfg_path_app = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "configs", "settings.json"))
+        cfg = self._merge_json_safely(cfg, cfg_path_app)
+
+        cfg["openai_api_key"] = load_api_key(cfg)
+        cfg["model_name"] = load_model_name(cfg)
+        cfg["temperature"] = load_temperature(cfg)
+
+        return cfg
+
+    def _merge_json_safely(self, base: Dict[str, Any], path: str) -> Dict[str, Any]:
+        try:
+            if os.path.exists(path) and os.path.getsize(path) > 0:
+                with open(path, "r", encoding="utf-8") as f:
+                    data = json.load(f)
+                if isinstance(data, dict):
+                    merged = dict(base)
+                    merged.update(data)
+                    return merged
+        except Exception:
+            pass
+        return base
\ No newline at end of file
```

</details>

<details><summary>config.example.json</summary>

```diff
diff --git a/config.example.json b/config.example.json
new file mode 100644
index 0000000..e5ef62e
--- /dev/null
+++ b/config.example.json
@@ -0,0 +1,11 @@
+{
+  "openai_api_key": "YOUR_OPENAI_API_KEY",
+  "model_name": "gpt-4o",
+  "temperature": 0.7
+}
+
+{
+  "auto_bugfix": true,
+  "max_fix_cycles": 2,
+  "auto_apply_patches": false
+}
\ No newline at end of file
```

</details>

<details><summary>config.json.save</summary>

```diff
diff --git a/config.json.save b/config.json.save
new file mode 100644
index 0000000..8b13789
--- /dev/null
+++ b/config.json.save
@@ -0,0 +1 @@
+
```

</details>

<details><summary>main.py</summary>

```diff
diff --git a/main.py b/main.py
index b65c0ab..8753fdf 100644
--- a/main.py
+++ b/main.py
@@ -1,0 +2 @@
+# -*- coding: utf-8 -*-
@@ -3,0 +5,2 @@
+from __future__ import annotations
+
@@ -7,10 +10,100 @@ import os
-from PyQt6.QtWidgets import QApplication
-from app.ui.main_window import MainWindow
-
-def main():
-    # Путь к файлу настроек (settings.json), где храним model_mode, model_name, local_paths и т.д.
-    config_path = os.path.join("app", "configs", "settings.json")
-    
-    if os.path.exists(config_path):
-        with open(config_path, "r", encoding="utf-8") as f:
-            config = json.load(f)
+import traceback
+from typing import Dict, Any, Optional
+
+# 🔔 Логирование — максимально рано
+from app.logger import setup_logging, log_info, log_warning, log_error, log_debug
+
+# Qt HiDPI до создания QApplication (без QWidget)
+try:
+    from PyQt6.QtCore import QCoreApplication, Qt
+    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
+    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)
+except Exception:
+    pass
+
+# --- Опциональные агентные импорты (не ломаем, если их нет) ---
+_AIDEON_AGENT_AVAILABLE = False
+try:
+    from app.agent.agent import AideonAgent            # type: ignore
+    from app.agent.bridge_self_improver import SelfImproverBridge  # type: ignore
+    from app.core.file_manager import FileManager, FileManagerConfig  # type: ignore
+    from app.modules.improver.patcher import CodePatcher  # type: ignore
+    _AIDEON_AGENT_AVAILABLE = True
+except Exception:
+    AideonAgent = None              # type: ignore
+    SelfImproverBridge = None       # type: ignore
+    FileManager = None              # type: ignore
+    FileManagerConfig = None        # type: ignore
+    CodePatcher = None              # type: ignore
+
+
+# ⬇️ Подхватываем .env РАНЬШЕ всего, чтобы окружение было доступно везде
+def _load_dotenv_early() -> None:
+    try:
+        from dotenv import load_dotenv  # type: ignore
+        repo_root = os.path.dirname(os.path.abspath(__file__))
+        env_path = os.path.join(repo_root, ".env")
+        loaded = load_dotenv(dotenv_path=env_path, override=True)
+        if loaded:
+            log_info(f".env загружен: {env_path}")
+        else:
+            log_warning(f".env не найден или пуст: {env_path} (это не ошибка, продолжаем)")
+    except Exception as e:
+        log_warning(f"Не удалось загрузить .env ранним этапом: {e}")
+
+
+def _safe_load_json(path: str) -> Dict[str, Any]:
+    """Безопасно читает JSON. Возвращает {} при любой ошибке."""
+    try:
+        if not os.path.exists(path):
+            log_debug(f"Конфиг не найден: {path}")
+            return {}
+        if os.path.getsize(path) == 0:
+            log_warning(f"Конфиг пустой (0 байт): {path}")
+            return {}
+        with open(path, "r", encoding="utf-8") as f:
+            data = json.load(f)
+        if isinstance(data, dict):
+            log_info(f"Конфиг прочитан: {path} (ключей: {len(data)})")
+            return data
+        log_warning(f"Конфиг не dict, проигнорирован: {path}")
+        return {}
+    except Exception as e:
+        log_warning(f"Не удалось прочитать JSON {path}: {e}")
+        return {}
+
+
+def _install_crash_hook() -> None:
+    def _hook(exc_type, exc, tb):
+        log_error("Необработанное исключение:\n" + "".join(traceback.format_exception(exc_type, exc, tb)))
+        sys.__excepthook__(exc_type, exc, tb)
+    sys.excepthook = _hook
+
+
+def _merge_configs(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
+    merged = dict(base)
+    merged.update(override or {})
+    return merged
+
+
+def _apply_env_overrides(cfg: Dict[str, Any]) -> None:
+    env_model = os.getenv("OPENAI_MODEL")
+    if env_model:
+        old = cfg.get("model_name")
+        cfg["model_name"] = env_model
+        log_info(f"OPENAI_MODEL переопределил model_name: {old!r} → {env_model!r}")
+
+    env_temp = os.getenv("OPENAI_TEMPERATURE")
+    if env_temp:
+        try:
+            old_t = cfg.get("temperature")
+            cfg["temperature"] = float(env_temp)
+            log_info(f"OPENAI_TEMPERATURE переопределил temperature: {old_t!r} → {cfg['temperature']!r}")
+        except ValueError:
+            log_warning(f"Некорректный OPENAI_TEMPERATURE={env_temp!r}, оставляем {cfg.get('temperature')!r}")
+
+    api_key = os.getenv("OPENAI_API_KEY") or cfg.get("openai_api_key")
+    if api_key:
+        head = str(api_key)[:6]
+        tail = str(api_key)[-4:]
+        log_info(f"OPENAI_API_KEY обнаружен (mask): {head}…{tail}")
@@ -18,2 +111,195 @@ def main():
-        config = {}
-        print(f"⚠️ Не найден {config_path}, используем пустой config.")
+        log_warning("OPENAI_API_KEY не найден ни в ENV, ни в config — запросы к OpenAI вернут 401")
+
+
+def _make_agent(repo_root: str, cfg: Dict[str, Any]) -> Optional["AideonAgent"]:
+    """Опциональная сборка агента. Возвращает None, если модулей нет/не подошла сигнатура."""
+    if not _AIDEON_AGENT_AVAILABLE:
+        log_warning("AideonAgent недоступен (модуль не найден). GUI продолжит работу без агента.")
+        return None
+    try:
+        root_path = os.path.abspath(repo_root)
+        base_dir = os.path.join(root_path)
+
+        fm_cfg = FileManagerConfig(  # type: ignore
+            base_dir=base_dir,
+            allowed_roots=[base_dir],
+            read_only_paths=[os.path.join(base_dir, ".git")],
+            backups_dirname=".aideon_backups",
+            create_missing_dirs=True,
+            atomic_write=True,
+        )
+        fm = FileManager(fm_cfg)  # type: ignore
+
+        patcher = CodePatcher(file_manager=fm)  # type: ignore
+
+        # --- Гибкая инициализация SelfImproverBridge (в разных ветках разная сигнатура)
+        bridge: Optional["SelfImproverBridge"] = None
+        try:
+            bridge = SelfImproverBridge(file_manager=fm, patcher=patcher)  # type: ignore
+        except TypeError:
+            try:
+                bridge = SelfImproverBridge(patcher=patcher)  # type: ignore
+            except Exception as e2:
+                log_warning(f"SelfImproverBridge недоступен: {e2}")
+                bridge = None
+
+        policy_path = os.path.join(root_path, "app", "agent", "policy_default.json")
+
+        # --- Гибкая инициализация AideonAgent
+        agent: Optional["AideonAgent"] = None
+        try:
+            agent = AideonAgent(  # type: ignore
+                file_manager=fm,
+                improver_bridge=bridge,
+                policy_path=policy_path,
+                config=cfg
+            )
+        except TypeError:
+            # ветка без file_manager в конструкторе
+            agent = AideonAgent(  # type: ignore
+                improver_bridge=bridge,
+                policy_path=policy_path,
+                config=cfg
+            )
+        log_info("AideonAgent инициализирован")
+        return agent
+    except Exception as e:
+        log_warning(f"Не удалось инициализировать AideonAgent: {e}")
+        return None
+
+
+def _maybe_cli_agent(argv: list[str], repo_root: str, cfg: Dict[str, Any]) -> Optional[int]:
+    """
+    Неблокирующие CLI-команды агента (опционально).
+    --agent-plan "<goal>"
+    --agent-run "<goal>" [--steps N]
+    """
+    if not argv:
+        return None
+
+    def _pos(flag: str) -> Optional[int]:
+        try:
+            return argv.index(flag)
+        except ValueError:
+            return None
+
+    i_plan = _pos("--agent-plan")
+    i_run = _pos("--agent-run")
+    if i_plan is None and i_run is None:
+        return None
+
+    agent = _make_agent(repo_root, cfg)
+    if agent is None:
+        log_error("Нельзя выполнить агентную CLI-команду: AideonAgent недоступен.")
+        return 2
+
+    if i_plan is not None:
+        try:
+            goal = argv[i_plan + 1]
+        except Exception:
+            log_error('Укажите цель после --agent-plan "..."')
+            return 2
+        # допустим, в агенте есть high-level planner; если нет — используйте .planner.make_plan
+        plan = agent.planner.build_high_level_plan(goal=goal)  # type: ignore
+        print(json.dumps(plan, ensure_ascii=False, indent=2))
+        return 0
+
+    if i_run is not None:
+        try:
+            goal = argv[i_run + 1]
+        except Exception:
+            log_error('Укажите цель после --agent-run "..."')
+            return 2
+        steps = 5
+        if "--steps" in argv:
+            try:
+                steps = int(argv[argv.index("--steps") + 1])
+            except Exception:
+                log_warning("Некорректный --steps, используем 5")
+        result = agent.run_autonomous(goal=goal, max_steps=steps)  # type: ignore
+        print(json.dumps(result, ensure_ascii=False, indent=2))
+        return 0
+
+    return None
+
+
+def _attach_agent_to_window(window, agent) -> None:
+    """
+    Универсальная попытка «подмешать» агента в уже созданное окно и потребовать отрисовать меню.
+    Это позволяет показать пункт «Агент» даже если старый MainWindow не принимал agent в __init__.
+    """
+    try:
+        if agent is None:
+            return
+        # сначала пробуем «официальный» сеттер
+        if hasattr(window, "set_agent") and callable(getattr(window, "set_agent")):
+            window.set_agent(agent)  # type: ignore
+            log_info("Агент привязан к окну через set_agent()")
+        else:
+            # fallback — просто присваиваем поле
+            setattr(window, "agent", agent)
+            log_info("Агент присвоен в window.agent (fallback)")
+
+        # просим окно создать/обновить меню агента (любой из методов, если есть)
+        if hasattr(window, "ensure_agent_menu") and callable(getattr(window, "ensure_agent_menu")):
+            window.ensure_agent_menu()  # type: ignore
+            log_info("ensure_agent_menu() вызвано — меню агента должно появиться")
+        elif hasattr(window, "_create_agent_menu") and callable(getattr(window, "_create_agent_menu")):
+            window._create_agent_menu()  # type: ignore
+            log_info("_create_agent_menu() вызвано — меню агента должно появиться")
+        else:
+            log_warning("В окне нет ensure_agent_menu/_create_agent_menu — проверьте реализацию MainWindow")
+    except Exception as e:
+        log_warning(f"Не удалось прикрепить агента к окну: {e}")
+
+
+def main() -> None:
+    # 0) Логи и краш-хук
+    setup_logging()
+    _install_crash_hook()
+    log_info("=== Старт Aideon ===")
+
+    # 1) .env как можно раньше
+    _load_dotenv_early()
+
+    # 2) Базовый корень репо
+    repo_root = os.path.dirname(os.path.abspath(__file__))
+    log_debug(f"Repo root: {repo_root}")
+
+    # 3) Конфиги
+    cfg: Dict[str, Any] = _safe_load_json(os.path.join(repo_root, "config.json"))
+    cfg = _merge_configs(cfg, _safe_load_json(os.path.join(repo_root, "app", "configs", "settings.json")))
+
+    # 4) ENV-переопределения + дефолты
+    _apply_env_overrides(cfg)
+    cfg.setdefault("model_name", "gpt-4o")
+    cfg.setdefault("temperature", 0.7)
+    log_info(f"Финальная конфигурация: model={cfg['model_name']!r}, temperature={cfg['temperature']!r}")
+
+    # 5) Агентные CLI-команды (если есть — выполняем и выходим)
+    cli_rc = _maybe_cli_agent(sys.argv[1:], repo_root, cfg)
+    if isinstance(cli_rc, int):
+        sys.exit(cli_rc)
+
+    # 6) Запуск GUI: создаём QApplication СНАЧАЛА, лениво импортируем MainWindow ПОТОМ
+    try:
+        from PyQt6.QtWidgets import QApplication  # импорт тут, раньше QWidget не трогаем
+        app = QApplication(sys.argv)
+
+        try:
+            from app.ui.main_window import MainWindow  # импорт только после QApplication
+        except Exception as e:
+            log_error(f"Ошибка импорта MainWindow: {e}")
+            raise
+
+        agent = _make_agent(repo_root, cfg)
+
+        # Если старый MainWindow без параметра agent — fallback + принудительное добавление меню
+        try:
+            window = MainWindow(config=cfg, agent=agent)  # type: ignore[call-arg]
+            # Если конструктор принял — всё равно попросим гарантировать меню
+            _attach_agent_to_window(window, agent)
+        except TypeError:
+            log_warning("MainWindow не поддерживает параметр 'agent'. Создаём окно без него и прикрепляем позже.")
+            window = MainWindow(config=cfg)  # type: ignore[call-arg]
+            _attach_agent_to_window(window, agent)
@@ -21 +307,5 @@ def main():
-    app = QApplication(sys.argv)
+        window.show()
+        log_info("Qt-приложение запущено")
+        rc = app.exec()
+        log_info(f"Qt-приложение завершилось с кодом {rc}")
+        sys.exit(rc)
@@ -23,3 +313,3 @@ def main():
-    # Создаём главное окно, передавая config
-    window = MainWindow(config=config)
-    window.show()
+    except Exception as e:
+        log_error(f"Критическая ошибка запуска UI: {e}")
+        raise
@@ -27 +316,0 @@ def main():
-    sys.exit(app.exec())
```

</details>