from dataclasses import asdict, dataclass, field
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
    image: str
    include_degraded_in_downtime: str
    monitor_type: MonitorType
    status: MonitorStatus
    tag: str
    default_status: MonitorStatus = MonitorStatus.NONE
    degraded_trigger: Optional[str] = None
    down_trigger: Optional[str] = None
    type_data: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def monitor_from_dict(data: dict) -> 'Monitor':
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
            image=data.get("image", ""),
            include_degraded_in_downtime=data.get("include_degraded_in_downtime", "NO"),
            monitor_type=MonitorType(data["monitor_type"]) if not isinstance(data["monitor_type"], MonitorType) else data["monitor_type"],
            status=MonitorStatus(data.get("status", "NONE")) if not isinstance(data.get("status", "NONE"), MonitorStatus) else data.get("status", "NONE"),
            tag=data.get("tag", ""),
            default_status=MonitorStatus(data.get("default_status", "NONE")) if not isinstance(data.get("default_status", "NONE"), MonitorStatus) else data.get("default_status", "NONE"),
            degraded_trigger=data.get("degraded_trigger"),
            down_trigger=data.get("down_trigger"),
            type_data=data.get("type_data", {}),
        )

    def monitor_to_dict(self) -> dict:
        d = self.__dict__.copy()
        d["default_status"] = self.default_status.value
        d["monitor_type"] = self.monitor_type.value
        d["status"] = self.status.value
        return d
    
@dataclass
class ConfigInstance:
    host: str
    port: int
    token: str
    folder: str

@dataclass
class Config:
    instances: Dict[str, ConfigInstance] = field(default_factory=dict)
    default: Optional[str] = None

    @staticmethod
    def from_dict(data: dict) -> "Config":
        instances = {
            name: ConfigInstance(**inst)
            for name, inst in data.get("instances", {}).items()
        }
        return Config(
            instances=instances,
            default=data.get("default")
        )

    def to_dict(self) -> dict:
        return {
            "instances": {name: asdict(inst) for name, inst in self.instances.items()},
            "default": self.default
        }