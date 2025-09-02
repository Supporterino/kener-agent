import logging
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timezone
from pathlib import Path
import yaml
import re

def apply_monitor_defaults(monitor: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply default values to a monitor dict if not present.
    """
    if not isinstance(monitor, dict):
        logging.error("apply_monitor_defaults called with non-dict: %s", monitor)
        return monitor

    defaults = {
        "cron": "* * * * *",
        "day_degraded_minimum_count": 1,
        "day_down_minimum_count": 1,
        "default_status": "NONE",
        "degraded_trigger": None,
        "down_trigger": None,
        "include_degraded_in_downtime": "NO",
        "status": "ACTIVE",
        "description": "",
    }

    if "created_at" not in monitor:
        monitor["created_at"] = datetime.now(timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )

    for key, value in defaults.items():
        monitor.setdefault(key, value)

    logging.debug("Monitor after applying defaults: %s", monitor)
    return monitor

def load_monitors_from_yaml(yaml_file: Path) -> List[Dict[str, Any]]:
    """
    Load monitors from a YAML file.
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

    logging.debug("Loaded %d monitors from %s", len(config["monitors"]), yaml_file)
    return config["monitors"]

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
    monitor: Dict[str, Any],
    get_monitor_by_tag_func: Callable[[str], Optional[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    For group monitors, resolve and attach child monitor details.
    get_monitor_by_tag_func should be a function(tag: str) -> Optional[Dict[str, Any]]
    """
    if not isinstance(monitor, dict):
        logging.error("resolve_group_monitors called with non-dict: %s", monitor)
        return monitor

    if monitor.get("monitor_type") != "GROUP":
        return monitor

    type_data = monitor.get("type_data", {})
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
                    "id": child_monitor.get("id"),
                    "tag": child_monitor.get("tag"),
                    "name": child_monitor.get("name"),
                    "selected": True,
                }
            )
        else:
            logging.warning("Child monitor with tag '%s' could not be resolved.", child_tag)

    monitor.setdefault("type_data", {})["monitors"] = resolved_children
    logging.info(
        "Resolved group '%s' monitors → %s", monitor.get("name"), resolved_children
    )
    logging.debug("Group monitor after resolving children: %s", monitor)
    return monitor

def validate_monitor(monitor: Dict[str, Any]) -> bool:
    """
    Validate a monitor definition. Returns True if valid, False otherwise.
    """
    required_fields = ["tag", "name", "monitor_type"]
    for field in required_fields:
        if field not in monitor:
            logging.error("Monitor missing required field '%s': %s", field, monitor)
            return False
    # Add more validation as needed
    logging.debug("Monitor validated: %s", monitor)
    return True