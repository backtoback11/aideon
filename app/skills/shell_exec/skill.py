from __future__ import annotations
import subprocess
from typing import Dict, Any

def run(cmd: str) -> Dict[str, Any]:
    """
    Опасный скилл — как правило блокируется SafetyGuardian по policy.
    """
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate(timeout=30)
    return {"code": p.returncode, "stdout": out[-5000:], "stderr": err[-5000:]}