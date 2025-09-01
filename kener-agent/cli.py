import logging
from typing import Any
from tabulate import tabulate
from pathlib import Path

from config import save_instance, load_config, set_default_instance, list_instances
from api import KenerAPI

def cmd_login(args: Any) -> None:
    """
    Save a new instance configuration.
    """
    save_instance(
        args.name, args.host, args.port, args.token, args.folder, args.default
    )

def cmd_apply(args: Any) -> None:
    """
    Apply monitors from YAML files to the API.
    """
    cfg = load_config(args.instance)
    host, port, token, folder = cfg["host"], cfg["port"], cfg["token"], cfg["folder"]

    api = KenerAPI(host, port, token)
    folder = args.folder if args.folder else folder
    yaml_files = KenerAPI.load_yaml_files_from_folder(folder)

    for yaml_file in yaml_files:
        logging.info("Processing file: %s", yaml_file)
        monitors = KenerAPI.load_monitors_from_yaml(yaml_file)
        for monitor in monitors:
            tag = monitor.get("tag")
            if tag and api.monitor_exists(tag):
                logging.info(
                    "Skipping creation of monitor '%s' (tag '%s').",
                    monitor.get("name"),
                    tag,
                )
                continue

            monitor = api.resolve_group_monitors(monitor)
            monitor = api.apply_monitor_defaults(monitor)
            api.create_monitor(monitor)

def cmd_set_default(args: Any) -> None:
    """
    Set the default instance.
    """
    set_default_instance(args.name)

def cmd_list(args: Any) -> None:
    """
    List all configured instances.
    """
    try:
        info = list_instances()
    except FileNotFoundError as e:
        logging.error(str(e))
        return

    instances = info["instances"]
    default_instance = info["default"]

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

def cmd_version(args: Any) -> None:
    """
    Print the agent version.
    """
    from .version import get_version
    print(get_version())