import logging
from typing import List, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
import yaml
import re

from classes import Monitor, MonitorType, MonitorStatus, MonitorCategory

def apply_monitor_defaults(monitor: Monitor) -> Monitor:
    """
    Apply default values to a Monitor object if not present.
    """
    if not isinstance(monitor, Monitor):
        logging.error("apply_monitor_defaults called with non-Monitor: %s", monitor)
        return monitor

    if not monitor.cron:
        monitor.cron = "* * * * *"
    if not monitor.day_degraded_minimum_count:
        monitor.day_degraded_minimum_count = 1
    if not monitor.day_down_minimum_count:
        monitor.day_down_minimum_count = 1
    if not monitor.default_status:
        monitor.default_status = MonitorStatus.NONE
    if not hasattr(monitor, "degraded_trigger"):
        monitor.degraded_trigger = None
    if not hasattr(monitor, "down_trigger"):
        monitor.down_trigger = None
    if not monitor.include_degraded_in_downtime:
        monitor.include_degraded_in_downtime = "NO"
    if not monitor.status:
        monitor.status = MonitorCategory.NONE
    if not monitor.description:
        monitor.description = ""
    if not monitor.created_at:
        monitor.created_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")

    logging.debug("Monitor after applying defaults: %s", monitor)
    return monitor

def load_monitors_from_yaml(yaml_file: Path) -> List[Monitor]:
    """
    Load monitors from a YAML file and return as Monitor objects.
    """
    try:
        with open(yaml_file, "r") as f:
            config = yaml.safe_load(f)
    except Exception as e:
        logging.error("Failed to load YAML file %s: %s", yaml_file, e)
        return []

    if not config or "monitors" not in config:
        logging.warning("No 'monitors' key found in YAML file %s", yaml_file)
        return []

    if not isinstance(config["monitors"], list):
        logging.error("'monitors' key in %s is not a list", yaml_file)
        return []

    monitors = []
    for m in config["monitors"]:
        try:
            monitors.append(Monitor.monitor_from_dict(m))
        except Exception as e:
            logging.error("Failed to parse monitor from YAML: %s", e)
            continue

    logging.debug("Loaded %d monitors from %s", len(monitors), yaml_file)
    return monitors

def load_yaml_files_from_folder(folder_path: str) -> List[Path]:
    """
    Load and return sorted YAML files from a folder.
    """
    folder = Path(folder_path)
    if not folder.exists():
        logging.error("Folder '%s' does not exist.", folder_path)
        raise ValueError(f"'{folder_path}' does not exist")
    if not folder.is_dir():
        logging.error("'%s' is not a directory.", folder_path)
        raise ValueError(f"'{folder_path}' is not a valid folder")

    yaml_files = sorted(
        [
            f
            for f in folder.iterdir()
            if f.is_file() and re.match(r"^\d{2}-.*\.yml$", f.name)
        ],
        key=lambda f: f.name,
    )
    if not yaml_files:
        logging.warning("No YAML files found in folder '%s'", folder_path)
    else:
        logging.info(
            "Found %d YAML files to process: %s",
            len(yaml_files),
            [f.name for f in yaml_files],
        )
    logging.debug("YAML files found: %s", yaml_files)
    return yaml_files

def resolve_group_monitors(
    monitor: Monitor,
    get_monitor_by_tag_func: Callable[[str], Optional[Monitor]],
) -> Monitor:
    """
    For group monitors, resolve and attach child monitor details.
    get_monitor_by_tag_func should be a function(tag: str) -> Optional[Monitor]
    """
    if not isinstance(monitor, Monitor):
        logging.error("resolve_group_monitors called with non-Monitor: %s", monitor)
        return monitor

    if monitor.monitor_type != MonitorType.GROUP:
        return monitor

    type_data = monitor.type_data or {}
    child_monitors = type_data.get("monitors", [])

    if not isinstance(child_monitors, list):
        logging.warning("Group monitor 'type_data.monitors' is not a list: %s", child_monitors)
        child_monitors = []

    resolved_children = []
    for child in child_monitors:
        child_tag = child.get("tag")
        if not child_tag:
            logging.warning("Group child monitor has no tag: %s", child)
            continue

        child_monitor = get_monitor_by_tag_func(child_tag)
        if child_monitor:
            resolved_children.append(
                {
                    "id": child_monitor.id,
                    "tag": child_monitor.tag,
                    "name": child_monitor.name,
                    "selected": True,
                }
            )
        else:
            logging.warning("Child monitor with tag '%s' could not be resolved.", child_tag)

    monitor.type_data["monitors"] = resolved_children
    logging.info(
        "Resolved group '%s' monitors → %s", monitor.name, resolved_children
    )
    logging.debug("Group monitor after resolving children: %s", monitor)
    return monitor

def validate_monitor(monitor: Monitor) -> bool:
    """
    Validate a monitor definition. Returns True if valid, False otherwise.
    """
    required_fields = ["tag", "name", "monitor_type"]
    for field in required_fields:
        if not getattr(monitor, field, None):
            logging.error("Monitor missing required field '%s': %s", field, monitor)
            return False
    # Add more validation as needed
    logging.debug("Monitor validated: %s", monitor)
    return True