import logging
from typing import Any, Set
from tabulate import tabulate

from config import save_instance, load_config, set_default_instance, list_instances
from api import KenerAPI
from monitor import (
    load_yaml_files_from_folder,
    load_monitors_from_yaml,
    validate_monitor,
)
from types import Monitor

def cmd_login(args: Any) -> None:
    """
    Save a new instance configuration.
    """
    try:
        if not args.name or not args.host or not args.token or not args.folder:
            logging.error("Missing required arguments for login.")
            return
        save_instance(
            args.name, args.host, args.port, args.token, args.folder, args.default
        )
        logging.info("Instance '%s' saved successfully.", args.name)
    except Exception as e:
        logging.error("Failed to save instance: %s", e)

def cmd_apply(args: Any) -> None:
    """
    Apply monitors from YAML files to the API.
    """
    try:
        cfg = load_config(args.instance)
    except Exception as e:
        logging.error("Failed to load config: %s", e)
        return

    try:
        host, port, token, folder = cfg["host"], cfg["port"], cfg["token"], cfg["folder"]
    except KeyError as e:
        logging.error("Missing required config key: %s", e)
        return

    api = KenerAPI(host, port, token)
    folder = args.folder if args.folder else folder

    try:
        yaml_files = load_yaml_files_from_folder(folder)
    except Exception as e:
        logging.error("Failed to load YAML files from folder '%s': %s", folder, e)
        return

    if not yaml_files:
        logging.warning("No YAML files found in folder '%s'", folder)
        return

    seen_tags: Set[str] = set()
    for yaml_file in yaml_files:
        logging.info("Processing file: %s", yaml_file)
        monitors = load_monitors_from_yaml(yaml_file)
        if not monitors:
            logging.warning("No monitors found in file: %s", yaml_file)
            continue
        for monitor in monitors:
            if not isinstance(monitor, Monitor):
                logging.warning("Invalid monitor object in %s: %s", yaml_file, monitor)
                continue
            tag = monitor.tag
            if not tag:
                logging.warning("Monitor in %s missing 'tag': %s", yaml_file, monitor)
                continue
            if tag in seen_tags:
                logging.warning("Duplicate monitor tag '%s' in YAML files.", tag)
                continue
            seen_tags.add(tag)
            if not validate_monitor(monitor):
                logging.warning("Invalid monitor definition in %s: %s", yaml_file, monitor)
                continue
            try:
                if api.monitor_exists(tag):
                    logging.info(
                        "Skipping creation of monitor '%s' (tag '%s').",
                        monitor.name,
                        tag,
                    )
                    continue
                api.create_monitor(monitor)
            except Exception as e:
                logging.error("Error processing monitor with tag '%s': %s", tag, e)

def cmd_set_default(args: Any) -> None:
    """
    Set the default instance.
    """
    try:
        set_default_instance(args.name)
        logging.info("Default instance set to '%s'", args.name)
    except Exception as e:
        logging.error("Failed to set default instance: %s", e)

def cmd_list(args: Any) -> None:
    """
    List all configured instances.
    """
    try:
        info = list_instances()
    except FileNotFoundError as e:
        logging.error(str(e))
        return
    except Exception as e:
        logging.error("Failed to list instances: %s", e)
        return

    instances = info.get("instances", {})
    default_instance = info.get("default")

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
    try:
        print(tabulate(table, headers=headers, tablefmt="fancy_grid"))
    except Exception as e:
        logging.error("Failed to print table: %s", e)
        for row in table:
            print(row)

def cmd_version(args: Any) -> None:
    """
    Print the agent version.
    """
    try:
        from version import get_version
        print(get_version())
    except Exception as e:
        logging.error("Failed to get version: %s", e)