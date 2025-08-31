import http.client
import yaml
import json
import logging
from urllib.parse import urlencode
from datetime import datetime, timezone
from pathlib import Path
import re
import argparse
from tabulate import tabulate

# -----------------------------
# Logging setup
# -----------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)


# -----------------------------
# Version helpers
# -----------------------------
def get_version() -> str:
    try:
        import importlib.metadata as importlib_metadata
    except ImportError:
        import importlib_metadata  # type: ignore

    try:
        return importlib_metadata.version("kener-agent")
    except importlib_metadata.PackageNotFoundError:
        # fallback for running from source
        try:
            import tomllib

            with open("pyproject.toml", "rb") as f:
                data = tomllib.load(f)
                return data["project"]["version"]
        except Exception:
            return "unknown"


# -----------------------------
# Config paths
# -----------------------------
CONFIG_DIR = Path.home() / ".config" / "kener-agent"
CONFIG_FILE = CONFIG_DIR / "config.yml"


def save_config(host: str, port: int, token: str, folder: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {"host": host, "port": port, "token": token, "folder": folder}
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)
    logging.info("Configuration saved to %s", CONFIG_FILE)


def save_instance(
    name: str, host: str, port: int, token: str, folder: str, set_default: bool = False
):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    if CONFIG_FILE.exists():
        with open(CONFIG_FILE, "r") as f:
            cfg = yaml.safe_load(f) or {}
    else:
        cfg = {}

    cfg.setdefault("instances", {})
    cfg["instances"][name] = {
        "host": host,
        "port": port,
        "token": token,
        "folder": folder,
    }

    if set_default or "default" not in cfg:
        cfg["default"] = name

    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)

    logging.info("Instance '%s' saved to %s", name, CONFIG_FILE)
    if set_default:
        logging.info("Instance '%s' set as default", name)


def load_config(instance: str | None = None) -> dict:
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")

    with open(CONFIG_FILE, "r") as f:
        cfg = yaml.safe_load(f) or {}

    instances = cfg.get("instances", {})
    if not instances:
        raise ValueError("No instances defined in config. Run `login` first.")

    if instance:
        if instance not in instances:
            raise ValueError(f"Instance '{instance}' not found in config.")
        return instances[instance]

    # fallback: use default
    default_instance = cfg.get("default")
    if not default_instance or default_instance not in instances:
        raise ValueError("No default instance set. Please set one with `set-default`.")
    return instances[default_instance]


def set_default_instance(name: str):
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}. Run `login` first.")

    with open(CONFIG_FILE, "r") as f:
        cfg = yaml.safe_load(f) or {}

    if "instances" not in cfg or name not in cfg["instances"]:
        raise ValueError(f"Instance '{name}' not found in config.")

    cfg["default"] = name
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)

    logging.info("Default instance set to '%s'", name)


# -----------------------------
# API + Monitor helpers
# -----------------------------
def monitor_exists(conn, headers, tag: str) -> bool:
    query = urlencode({"tag": tag})
    path = f"/api/monitor?{query}"
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")

    if res.status != 200:
        logging.warning(
            "Failed to check monitor with tag '%s' → %s: %s", tag, res.status, data
        )
        return False

    try:
        monitors = json.loads(data)
        exists = len(monitors) > 0
        if exists:
            logging.info("Monitor with tag '%s' already exists.", tag)
        return exists
    except json.JSONDecodeError:
        logging.error(
            "Invalid JSON response while checking monitor with tag '%s': %s", tag, data
        )
        return False


def get_monitor_by_tag(conn, headers, tag: str) -> dict | None:
    query = urlencode({"tag": tag})
    path = f"/api/monitor?{query}"
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    data = res.read().decode("utf-8")

    if res.status != 200:
        logging.warning(
            "Failed to fetch monitor with tag '%s' → %s: %s", tag, res.status, data
        )
        return None

    try:
        monitors = json.loads(data)
        if isinstance(monitors, list) and monitors:
            monitor = monitors[0]
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


def resolve_group_monitors(conn, headers, monitor: dict) -> dict:
    if monitor.get("monitor_type") != "GROUP":
        return monitor

    type_data = monitor.get("type_data", {})
    child_monitors = type_data.get("monitors", [])

    resolved_children = []
    for child in child_monitors:
        child_tag = child.get("tag")
        if not child_tag:
            logging.warning("Group child monitor has no tag: %s", child)
            continue

        child_monitor = get_monitor_by_tag(conn, headers, child_tag)
        if child_monitor:
            resolved_children.append(
                {
                    "id": child_monitor.get("id"),
                    "tag": child_monitor.get("tag"),
                    "name": child_monitor.get("name"),
                    "selected": True,
                }
            )

    monitor["type_data"]["monitors"] = resolved_children
    logging.info(
        "Resolved group '%s' monitors → %s", monitor.get("name"), resolved_children
    )
    return monitor


def apply_monitor_defaults(monitor: dict) -> dict:
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

    return monitor


def create_monitor(conn, headers, monitor: dict):
    payload = json.dumps(monitor)
    conn.request("POST", "/api/monitor", payload, headers)

    res = conn.getresponse()
    data = res.read().decode("utf-8")

    if res.status == 201:
        logging.info("Monitor '%s' created successfully.", monitor.get("name"))
    else:
        logging.error(
            "Failed to create monitor '%s' → %s: %s",
            monitor.get("name"),
            res.status,
            data,
        )


def load_yaml_files_from_folder(folder_path: str):
    folder = Path(folder_path)
    if not folder.is_dir():
        raise ValueError(f"'{folder_path}' is not a valid folder")

    yaml_files = sorted(
        [
            f
            for f in folder.iterdir()
            if f.is_file() and re.match(r"^\d{2}-.*\.yml$", f.name)
        ],
        key=lambda f: f.name,
    )
    logging.info(
        "Found %d YAML files to process: %s",
        len(yaml_files),
        [f.name for f in yaml_files],
    )
    return yaml_files


# -----------------------------
# Commands
# -----------------------------
def cmd_login(args):
    save_instance(
        args.name, args.host, args.port, args.token, args.folder, args.default
    )


def cmd_apply(args):
    cfg = load_config(args.instance)
    host, port, token, folder = cfg["host"], cfg["port"], cfg["token"], cfg["folder"]

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    conn = http.client.HTTPConnection(host, port)

    folder = args.folder if args.folder else folder
    yaml_files = load_yaml_files_from_folder(folder)

    for yaml_file in yaml_files:
        logging.info("Processing file: %s", yaml_file)
        with open(yaml_file, "r") as f:
            config = yaml.safe_load(f)

        for monitor in config.get("monitors", []):
            tag = monitor.get("tag")
            if tag and monitor_exists(conn, headers, tag):
                logging.info(
                    "Skipping creation of monitor '%s' (tag '%s').",
                    monitor.get("name"),
                    tag,
                )
                continue

            monitor = resolve_group_monitors(conn, headers, monitor)
            monitor = apply_monitor_defaults(monitor)
            create_monitor(conn, headers, monitor)


def cmd_set_default(args):
    set_default_instance(args.name)


def cmd_list(args):
    if not CONFIG_FILE.exists():
        logging.error("No config file found at %s", CONFIG_FILE)
        return

    with open(CONFIG_FILE, "r") as f:
        cfg = yaml.safe_load(f) or {}

    instances = cfg.get("instances", {})
    default_instance = cfg.get("default")

    if not instances:
        logging.info("No instances configured.")
        return

    table = []
    for name, inst in instances.items():
        marker = "*" if name == default_instance else ""
        table.append(
            [marker, name, inst.get("host"), inst.get("port"), inst.get("folder")]
        )

    headers = ["Default", "Instance", "Host", "Port", "Folder"]
    print(tabulate(table, headers=headers, tablefmt="fancy_grid"))


def cmd_version(args):
    print(get_version())


def cmd_set_instance(args):
    config = load_config()
    if args.name not in config.get("instances", {}):
        logging.error("Instance '%s' not found.", args.name)
    config["default"] = args.name
    save_config(config)
    logging.info("Default context switched to '%s'", args.name)


# -----------------------------
# CLI entrypoint
# -----------------------------
def main():
    parser = argparse.ArgumentParser(prog="kener-agent", description="Kener Agent CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # login command
    login_parser = subparsers.add_parser(
        "login", help="Save API connection settings for an instance"
    )
    login_parser.add_argument(
        "--name", required=True, help="Name of the instance (e.g. dev, prod)"
    )
    login_parser.add_argument("--host", required=True, help="API host, e.g., 10.10.3.1")
    login_parser.add_argument(
        "--port", type=int, default=3000, help="API port, default 3000"
    )
    login_parser.add_argument(
        "--token", required=True, help="Bearer token for API authentication"
    )
    login_parser.add_argument(
        "--folder", required=True, help="Folder containing YAML files to process"
    )
    login_parser.add_argument(
        "--default", action="store_true", help="Set this instance as default"
    )
    login_parser.set_defaults(func=cmd_login)

    # apply command
    apply_parser = subparsers.add_parser("apply", help="Apply monitors from YAML files")
    apply_parser.add_argument("--instance", help="Instance to use (overrides default)")
    apply_parser.add_argument("--folder", help="Optional override folder")
    apply_parser.set_defaults(func=cmd_apply)

    # set-default command
    def_parser = subparsers.add_parser("set-default", help="Set the default instance")
    def_parser.add_argument("name", help="Instance name to set as default")
    def_parser.set_defaults(func=cmd_set_default)

    # list command
    list_parser = subparsers.add_parser("list", help="List all configured instances")
    list_parser.set_defaults(func=cmd_list)

    # version
    version_parser = subparsers.add_parser("version", help="Print agent version")
    version_parser.set_defaults(func=cmd_version)

    # set-instance
    set_instance_parser = subparsers.add_parser(
        "set-instance", help="Set default instance"
    )
    set_instance_parser.add_argument("name", help="Instance name to use as default")
    set_instance_parser.set_defaults(func=cmd_set_instance)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
