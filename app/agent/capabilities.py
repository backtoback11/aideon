from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, List
import platform
import shutil
import os

from app.logger import log_info

@dataclass
class Capability:
    name: str
    present: bool
    details: Dict[str, Any]

class CapabilityDiscovery:
    """
    Лёгкое авто-обнаружение возможностей устройства.
    Можно расширять плагинами (ROS, GPIO, камеры и т.д.)
    """
    def scan(self) -> List[Capability]:
        caps: List[Capability] = []
        caps.append(Capability("os", True, {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        }))
        caps.append(Capability("docker", shutil.which("docker") is not None, {}))
        caps.append(Capability("git", shutil.which("git") is not None, {}))
        caps.append(Capability("camera_dev", os.path.exists("/dev/video0"), {}))
        caps.append(Capability("network", True, {"curl": shutil.which("curl") is not None}))
        log_info(f"[CapabilityDiscovery] найдено {len(caps)} capability")
        return caps