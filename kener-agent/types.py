from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from enum import Enum

class MonitorStatus(Enum):
    NONE = "NONE"
    UP = "UP"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"

class MonitorType(Enum):
    API = "API"
    PING = "PING"
    DNS = "DNS"
    TCP = "TCP"
    GROUP = "GROUP"
    SSL = "SSL"
    SQL = "SQL"

@dataclass
class Monitor:
    id: int
    name: str
    description: str
    category_name: str
    created_at: str
    updated_at: str
    cron: str
    day_degraded_minimum_count: int
    day_down_minimum_count: int
    default_status: MonitorStatus = MonitorStatus.NONE
    degraded_trigger: Optional[str] = None
    down_trigger: Optional[str] = None
    image: str
    include_degraded_in_downtime: str
    monitor_type: MonitorType
    status: MonitorStatus
    tag: str
    type_data: Dict[str, Any] = field(default_factory=dict)

def monitor_from_dict(data: dict) -> Monitor:
    return Monitor(
        id=data["id"],
        name=data["name"],
        description=data.get("description", ""),
        category_name=data.get("category_name", ""),
        created_at=data.get("created_at", ""),
        updated_at=data.get("updated_at", ""),
        cron=data.get("cron", "* * * * *"),
        day_degraded_minimum_count=data.get("day_degraded_minimum_count", 1),
        day_down_minimum_count=data.get("day_down_minimum_count", 1),
        default_status=MonitorStatus(data.get("default_status", "NONE")),
        degraded_trigger=data.get("degraded_trigger"),
        down_trigger=data.get("down_trigger"),
        image=data.get("image", ""),
        include_degraded_in_downtime=data.get("include_degraded_in_downtime", "NO"),
        monitor_type=MonitorType(data["monitor_type"]),
        status=MonitorStatus(data.get("status", "NONE")),
        tag=data["tag"],
        type_data=data.get("type_data", {}),
    )

def monitor_to_dict(monitor: Monitor) -> dict:
    d = monitor.__dict__.copy()
    d["default_status"] = monitor.default_status.value
    d["monitor_type"] = monitor.monitor_type.value
    d["status"] = monitor.status.value
    return d