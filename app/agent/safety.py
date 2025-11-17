from __future__ import annotations
from typing import Dict, Any, Tuple, List
from app.logger import log_info

class SafetyGuardian:
    """
    Мини-политика безопасности.
    Политика = dict, например:
      {
        "profile": "restricted",
        "net_disabled": true,
        "allow_shell": false,
        "fs_write_whitelist": ["README.md"]
      }
    """
    def __init__(self, policy: Dict[str, Any]):
        self.policy = policy or {}

    def check(self, skill_manifest: Dict[str, Any], args: Dict[str, Any]) -> Tuple[bool, str]:
        perms: List[str] = skill_manifest.get("permissions", [])
        prof = self.policy.get("profile", "default")

        # запрет сети
        if self.policy.get("net_disabled") and any(p.startswith("net.") for p in perms):
            return False, "Network disabled by policy"

        # контроль shell
        if not self.policy.get("allow_shell", False) and any(p == "proc.shell" for p in perms):
            return False, "Shell execution disabled by policy"

        # файловые записи
        if any(p == "fs.write" for p in perms):
            wl = set(self.policy.get("fs_write_whitelist", []))
            path = str(args.get("path", ""))
            if wl and path not in wl:
                return False, f"Write denied for {path} (not in whitelist)"

        log_info(f"[Safety] OK skill={skill_manifest.get('name')} profile={prof}")
        return True, ""