import http.client
import json
import logging
from typing import List, Optional

from .types import Monitor
from .monitor import (
    apply_monitor_defaults,
    resolve_group_monitors,
)

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

    def get_monitor_by_tag(self, tag: str) -> Optional[Monitor]:
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
                monitor = Monitor.monitor_from_dict(monitors[0])
                logging.debug("Fetched monitor for tag '%s': %s", tag, monitor)
                logging.info("Resolved tag '%s' → monitor id '%s'", tag, monitor.id)
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
        
    def get_monitors(self) -> List[Monitor]:
        """
        Fetch all monitors.
        """
        try:
            self.conn.request("GET", "/api/monitor", headers=self.headers)
            res = self.conn.getresponse()
            data = res.read().decode("utf-8")
        except Exception as e:
            logging.error("Network error while fetching monitors: %s", e)
            return None

        if res.status != 200:
            logging.warning(
                "Failed to fetch monitors → %s: %s",res.status, data
            )
            return None
        
        try:
            monitors = json.loads(data)
            if isinstance(monitors, list) and monitors:
                resolved_monitors = []
                for monitor in monitors:
                    resolved_monitors.append(Monitor.monitor_from_dict(monitor))
                return resolved_monitors
            else:
                logging.warning("No monitors found")
                return None
        except json.JSONDecodeError:
            logging.error(
                "Invalid JSON response while fetching monitors: %s",
                data,
            )
            return None

    def create_monitor(self, monitor: Monitor) -> None:
        """
        Create a new monitor via the API.
        """
        if not isinstance(monitor, Monitor):
            logging.error("create_monitor called with non-Monitor: %s", monitor)
            return

        # Use monitor helpers for group resolution and defaults
        monitor = resolve_group_monitors(monitor, self.get_monitor_by_tag)
        monitor = apply_monitor_defaults(monitor)

        try:
            payload = json.dumps(monitor.monitor_to_dict())
        except Exception as e:
            logging.error("Failed to serialize monitor to JSON: %s", e)
            return

        try:
            self.conn.request("POST", "/api/monitor", payload, self.headers)
            res = self.conn.getresponse()
            data = res.read().decode("utf-8")
        except Exception as e:
            logging.error("Network error while creating monitor '%s': %s", monitor.name, e)
            return

        if res.status == 201:
            logging.info("Monitor '%s' created successfully.", monitor.name)
            logging.debug("API response: %s", data)
        else:
            logging.error(
                "Failed to create monitor '%s' → %s: %s",
                monitor.name,
                res.status,
                data,
            )