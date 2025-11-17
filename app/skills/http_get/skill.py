from __future__ import annotations
from typing import Dict, Any
import json

try:
    import requests  # опционально
except Exception:
    requests = None  # type: ignore

from app.logger import log_warning

def run(url: str, timeout: int = 10) -> Dict[str, Any]:
    if requests is None:
        log_warning("[http.get] модуль requests не установлен")
        return {"ok": False, "error": "requests not installed"}
    try:
        r = requests.get(url, timeout=timeout)
        # не возвращаем гигантские тела
        body = r.text[:10000]
        return {"ok": True, "status": r.status_code, "body": body}
    except Exception as e:
        return {"ok": False, "error": str(e)}