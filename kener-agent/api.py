import http.client
import json
import logging
import re
from pathlib import Path
from typing import Optional, Any, Dict, List
from datetime import datetime, timezone
import yaml

class KenerAPI:
    """
    API client for interacting with the Kener Agent backend.
    """

    def __init__(self, host: str, port: int, token: str):
        self.host = host
        self.port = port
        self.token = token
        try:
            self.conn = http.client.HTTPConnection(host, port, timeout=10)
        except Exception as e:
            logging.error("Failed to create HTTP connection to %s:%s: %s", host, port, e)
            raise
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        }
        logging.debug("Initialized KenerAPI with host=%s, port=%s", host, port)

    def monitor_exists(self, tag: str) -> bool:
        """
        Check if a monitor with the given tag exists.
        """
        from urllib.parse import urlencode

        if not tag:
            logging.error("monitor_exists called with empty tag")
            return False

        query = urlencode({"tag": tag})
        path = f"/api/monitor?{query}"
        try:
            self.conn.request("GET", path, headers=self.headers)
            res = self.conn.getresponse()
            data = res.read().decode("utf-8")
        except Exception as e:
            logging.error("Network error while checking monitor '%s': %s", tag, e)
            return False

        if res.status != 200:
            logging.warning(
                "Failed to check monitor with tag '%s' → %s: %s", tag, res.status, data
            )
            return False

        try:
            monitors = json.loads(data)
            exists = isinstance(monitors, list) and len(monitors) > 0
            logging.debug("Monitor check for tag '%s': exists=%s, response=%s", tag, exists, monitors)
            if exists:
                logging.info("Monitor with tag '%s' already exists.", tag)
            return exists
        except json.JSONDecodeError:
            logging.error(
                "Invalid JSON response while checking monitor with tag '%s': %s", tag, data
            )
            return False

    def get_monitor_by_tag(self, tag: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a monitor by its tag.
        """
        from urllib.parse import urlencode

        if not tag:
            logging.error("get_monitor_by_tag called with empty tag")
            return None

        query = urlencode({"tag": tag})
        path = f"/api/monitor?{query}"
        try:
            self.conn.request("GET", path, headers=self.headers)
            res = self.conn.getresponse()
            data = res.read().decode("utf-8")
        except Exception as e:
            logging.error("Network error while fetching monitor '%s': %s", tag, e)
            return None

        if res.status != 200:
            logging.warning(
                "Failed to fetch monitor with tag '%s' → %s: %s", tag, res.status, data
            )
            return None

        try:
            monitors = json.loads(data)
            if isinstance(monitors, list) and monitors:
                monitor = monitors[0]
                logging.debug("Fetched monitor for tag '%s': %s", tag, monitor)
                logging.info("Resolved tag '%s' → monitor id '%s'", tag, monitor.get("id"))
                return monitor
            else:
                logging.warning("No monitor found for tag '%s'", tag)
                return None
        except json.JSONDecodeError:
            logging.error(
                "Invalid JSON response while fetching monitor id for tag '%s': %s",
                tag,
                data,
            )
            return None

    def resolve_group_monitors(self, monitor: Dict[str, Any]) -> Dict[str, Any]:
        """
        For group monitors, resolve and attach child monitor details.
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

            child_monitor = self.get_monitor_by_tag(child_tag)
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

    def apply_monitor_defaults(self, monitor: Dict[str, Any]) -> Dict[str, Any]:
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

    def create_monitor(self, monitor: Dict[str, Any]) -> None:
        """
        Create a new monitor via the API.
        """
        if not isinstance(monitor, dict):
            logging.error("create_monitor called with non-dict: %s", monitor)
            return

        try:
            payload = json.dumps(monitor)
        except Exception as e:
            logging.error("Failed to serialize monitor to JSON: %s", e)
            return

        try:
            self.conn.request("POST", "/api/monitor", payload, self.headers)
            res = self.conn.getresponse()
            data = res.read().decode("utf-8")
        except Exception as e:
            logging.error("Network error while creating monitor '%s': %s", monitor.get("name"), e)
            return

        if res.status == 201:
            logging.info("Monitor '%s' created successfully.", monitor.get("name"))
            logging.debug("API response: %s", data)
        else:
            logging.error(
                "Failed to create monitor '%s' → %s: %s",
                monitor.get("name"),
                res.status,
                data,
            )

    @staticmethod
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

    @staticmethod
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