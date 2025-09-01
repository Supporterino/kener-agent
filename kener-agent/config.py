from pathlib import Path
from typing import Optional, Dict, Any
import yaml
import logging

CONFIG_DIR = Path.home() / ".config" / "kener-agent"
CONFIG_FILE = CONFIG_DIR / "config.yml"


def save_config(host: str, port: int, token: str, folder: str) -> None:
    """
    Save a simple config (single instance) to the config file.
    """
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    cfg = {"host": host, "port": port, "token": token, "folder": folder}
    with open(CONFIG_FILE, "w") as f:
        yaml.safe_dump(cfg, f, default_flow_style=False)
    logging.info("Configuration saved to %s", CONFIG_FILE)


def save_instance(
    name: str,
    host: str,
    port: int,
    token: str,
    folder: str,
    set_default: bool = False,
) -> None:
    """
    Save an instance configuration under a given name.
    Optionally set as default.
    """
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


def load_config(instance: Optional[str] = None) -> Dict[str, Any]:
    """
    Load configuration for a given instance.
    If no instance is specified, load the default.
    """
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


def set_default_instance(name: str) -> None:
    """
    Set the default instance by name.
    """
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


def list_instances() -> Dict[str, Any]:
    """
    Return all configured instances and the default.
    """
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"No config found at {CONFIG_FILE}.")

    with open(CONFIG_FILE, "r") as f:
        cfg = yaml.safe_load(f) or {}

    instances = cfg.get("instances", {})
    default_instance = cfg.get("default")
    return {"instances": instances, "default": default_instance}